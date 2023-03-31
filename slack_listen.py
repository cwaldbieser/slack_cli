#! /usr/bin/env python

import pathlib
import queue
import threading

import logzero
import toml
from logzero import logger
from rich.markup import escape
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slackcli.channel import get_channel_info, get_channels
from slackcli.console import console
from slackcli.message import display_message_item
from slackcli.user import get_users

app = None
q = queue.Queue()
current_channel = None


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
    get_channels(config)
    get_users(config)
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    SocketModeHandler(app, app_token).start()
    q.join()


def worker(config):

    while True:
        task_type, data = q.get()
        if task_type == "display":
            worker_display_message(data, config)
        q.task_done()


def worker_display_message(data, config):
    """
    Display a message.
    """
    channel_id, message = data
    check_display_channel(channel_id)
    display_message_item(message, config)


def check_display_channel(channel_id):
    """
    Determine if the channel banner needs to be displayed.
    Display it as needed.
    """
    global current_channel
    if channel_id != current_channel:
        display_channel_banner(channel_id)
        current_channel = channel_id


def display_channel_banner(channel_id):
    """
    Display the channel banner.
    """
    global style
    channel_info = get_channel_info(channel_id)
    channel_name = channel_info["name"]
    console.rule(f"[channel]{escape(channel_name)}[/channel]")


def start_worker_thread(config):
    """
    Start the thread responsible for writing to the display.
    """
    # Turn-on the worker thread.
    threading.Thread(target=worker, daemon=True, args=(config,)).start()


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


def queue_message(channel_id, msg):
    """
    Queue a message to be displayed.
    """
    q.put(("display", (channel_id, msg)))


# Start your app
if __name__ == "__main__":
    init()


@app.event("message")
def handle_message_events(body, logger):
    event = body["event"]
    event_subtype = event.get("subtype")
    if event_subtype in ("message_deleted", "message_changed"):
        return
    channel_id = event["channel"]
    queue_message(channel_id, event)


@app.event("file_shared")
def handle_file_shared_events(body, logger):
    pass


@app.event("file_created")
def handle_file_created_events(body, logger):
    pass


# Start your app
if __name__ == "__main__":
    main()