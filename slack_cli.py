#! /usr/bin/env python

import pathlib
import queue
import re
import subprocess
import tempfile
import threading
import xml.sax.saxutils

import httpx
import logzero
import toml
from logzero import logger
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = None
channel_map = None
user_map = None
image_types = frozenset(["image/jpeg", "image/png", "image/gif"])
q = queue.Queue()


def init():
    """
    Initialize application.
    """
    global app
    logger.info("Loading application configuration.")
    config = load_config()
    log_level = config.get("logging", {"severity": "INFO"}).get("severity", "INFO")
    if log_level in ("ERROR", "WARN", "INFO", "DEBUG"):
        severity = getattr(logzero, log_level)
    else:
        severity = "INFO"
    logzero.loglevel(severity)
    init_app(config)


def main():
    """
    Main program entrypoint.
    """
    global app
    config = load_config()
    start_worker_thread(config)
    get_channels(app.client)
    get_users(app.client)
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    SocketModeHandler(app, app_token).start()
    q.join()


def display_message(msg):
    """
    Queue a message to be displayed.
    """
    q.put(("display", msg))


def worker(config):
    while True:
        task_type, data = q.get()
        if task_type == "display":
            logger.info(data)
        elif task_type == "download_file":
            worker_download_file(config, data)
        q.task_done()


def worker_download_file(config, data):
    """
    Download a file.
    """
    global image_types
    global channel_map
    team_id, file_id, channel_id = data
    channel_name = channel_map[channel_id]["name"]
    user_token = config["oauth"]["user_token"]
    params = {"file": file_id}
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/files.info"
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        logger.error(
            f"Got status {r.status_code} when fetching metadata for file with id {file_id}."
        )
        return
    json_response = r.json()
    file_info = json_response["file"]
    private_url = file_info["url_private"]
    title = file_info["title"]
    mime_type = file_info["mimetype"]
    r = httpx.get(private_url, headers=headers)
    if r.status_code != 200:
        logger.error(
            f"Got status {r.status_code} when fetching file with id {file_id}."
        )
        return
    with tempfile.NamedTemporaryFile(delete=False) as f:
        for data in r.iter_bytes():
            f.write(data)
        temp_name = f.name
        logger.debug(f"mimetype: {mime_type}, image_types: {image_types}")
        if mime_type in image_types:
            logger.info(f"[{channel_name}] =<{title}>=")
            cmd = ("kitty", "+kitten", "icat", temp_name)
            logger.debug(f"cmd: {cmd}")
            result = subprocess.run(cmd)
            logger.debug(f"returncode: {result.returncode}")


def start_worker_thread(config):
    """
    Start the thread responsible for writing to the display.
    """
    # Turn-on the worker thread.
    threading.Thread(target=worker, daemon=True, args=(config,)).start()


def get_users(client):
    """
    Get users.
    """
    global user_map
    user_map = {}
    response = client.users_list()
    users = response["members"]
    for user in users:
        user_id = user["id"]
        user_info = {}
        user_info["name"] = user["name"]
        user_map[user_id] = user_info


def get_channels(client):
    """
    Get channels.
    """
    global channel_map
    response = client.conversations_list()
    channels = response["channels"]
    channel_map = {}
    for channel in channels:
        channel_id = channel["id"]
        channel_info = {}
        is_archived = channel["is_archived"]
        if is_archived:
            continue
        channel_info["name"] = channel["name"]
        channel_info["is_channel"] = channel["is_channel"]
        channel_info["is_group"] = channel["is_group"]
        channel_info["is_im"] = channel["is_im"]
        channel_info["is_mpim"] = channel["is_mpim"]
        channel_info["is_private"] = channel["is_private"]
        channel_map[channel_id] = channel_info


def load_config():
    """
    Load config.
    """
    pth = pathlib.Path("~/.slackcli/waldbiec-dev.toml").expanduser()
    with open(pth, "r") as f:
        config = toml.load(f)
    return config


def init_app(config):
    """
    Initialize app.
    """
    global app
    # Initializes your app with your bot token and socket mode handler
    logger.info("Initializing/authorizing application.")
    user_token = config["oauth"]["user_token"]
    app = App(token=user_token)


def display_file(team_id, file_id, channel_id):
    """
    Queue file to be downloaded and displayed.
    """
    q.put(("download_file", (team_id, file_id, channel_id)))


# Start your app
if __name__ == "__main__":
    init()


@app.message(re.compile("(.*)"))
def handle_message(say, context):
    """
    Handle plain old text messages.
    """
    global channel_map
    global user_map
    channel_id = context["channel_id"]
    channel_info = channel_map[channel_id]
    channel_name = channel_info["name"]
    user_id = context["user_id"]
    user_name = user_map[user_id]["name"]
    matches = context["matches"]
    matches = [xml.sax.saxutils.unescape(m) for m in matches]
    message = "\n".join(matches)
    message = f"[{channel_name}][{user_name}] {message}"
    display_message(message)
    # logger.info(f"[{channel_name}][{user_name}] {message}")
    # logger.debug(context)


@app.event("message")
def handle_message_events(body, logger):
    handle_message_events_(body)


def handle_message_events_(body):
    """
    Handle message events that don't match the standard handler.
    """
    logger.debug(body)


@app.event("file_created")
def handle_file_created_events(body, logger):
    handle_file_events_("file_created", body)


@app.event("file_shared")
def handle_file_shared_events(body, logger):
    handle_file_events_("file_shared", body)


def handle_file_events_(event_type, body):
    """
    Handle file events.
    """
    if event_type == "file_shared":
        team_id = body["team_id"]
        file_id = body["event"]["file_id"]
        channel_id = body["event"]["channel_id"]
        display_file(team_id, file_id, channel_id)
    logger.debug(f"[{event_type}]: {body}")


# Start your app
if __name__ == "__main__":
    main()
