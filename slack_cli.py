#! /usr/bin/env python

import pathlib
import re

import logzero
import toml
from logzero import logger
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = None
channel_map = None
user_map = None


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
    get_channels(app.client)
    get_users(app.client)
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    SocketModeHandler(app, app_token).start()


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
    logger.debug(channel_map)


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


# Start your app
if __name__ == "__main__":
    init()


@app.message(re.compile("(.*)"))
def handle_message(say, context):
    """
    context looks like:

    """
    global channel_map
    global user_map
    channel_id = context["channel_id"]
    channel_info = channel_map[channel_id]
    channel_name = channel_info["name"]
    user_id = context["user_id"]
    user_name = user_map[user_id]["name"]
    matches = context["matches"]
    message = '\n'.join(matches)
    logger.info(f"[{channel_name}][{user_name}] {message}")
    logger.debug(context)


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
    logger.debug(f"[{event_type}]: {body}")


# Start your app
if __name__ == "__main__":
    main()
