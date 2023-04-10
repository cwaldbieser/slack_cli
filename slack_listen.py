#! /usr/bin/env python

import argparse
import queue
import threading

import logzero
from logzero import logger
from rich.markup import escape
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slackcli.channel import (
    get_all_channel_ids,
    get_channel_id_by_name,
    get_channel_info,
    load_channels,
)
from slackcli.config import load_config
from slackcli.console import console
from slackcli.filecache import init_filecache
from slackcli.message import display_message_item
from slackcli.user import get_users

app = None
q = queue.Queue()
current_channel = None


def init(args):
    """
    Initialize application.
    """
    logger.info("Loading application configuration.")
    config = load_config(args.workspace)
    log_level = config.get("logging", {"severity": "INFO"}).get("severity", "INFO")
    if log_level in ("ERROR", "WARN", "INFO", "DEBUG"):
        severity = getattr(logzero, log_level)
    else:
        severity = "INFO"
    logzero.loglevel(severity)
    init_app(config)


def main(args):
    """
    Main program entrypoint.
    """
    global app
    config = load_config(args.workspace)
    load_channels(config)
    get_users(config)
    listening = create_channel_filters(config)
    start_worker_thread(config, args.workspace, listening)
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    SocketModeHandler(app, app_token).start()
    q.join()


def create_channel_filters(config):
    """
    Create channel filters.
    """
    channel_ids = get_all_channel_ids()
    default = {"listen_allow": "*"}
    channels_cfg = config.get("channels", default)
    listen_allow = channels_cfg.get("listen_allow", default["listen_allow"])
    listen_deny = channels_cfg.get("listen_deny", [])
    if listen_allow == "*":
        listen_allow = channel_ids
    else:
        listen_allow = set([get_channel_id_by_name(chname) for chname in listen_allow])
    listen_deny = set([get_channel_id_by_name(chname) for chname in listen_deny])
    listening = listen_allow - listen_deny
    return listening


def worker(config, workspace, listening):

    with init_filecache(args.workspace) as filecache:
        while True:
            task_type, data = q.get()
            if task_type == "display":
                worker_display_message(data, config, filecache, listening)
            q.task_done()


def worker_display_message(data, config, filecache, listening):
    """
    Display a message.
    """
    global app
    channel_id, message = data
    if channel_id not in listening:
        return
    check_display_channel(channel_id)
    display_message_item(message, config, filecache)
    ts = message["ts"]
    app.client.conversations_mark(channel=channel_id, ts=ts)


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


def start_worker_thread(config, workspace, listening):
    """
    Start the thread responsible for writing to the display.
    """
    # Turn-on the worker thread.
    threading.Thread(
        target=worker, daemon=True, args=(config, workspace, listening)
    ).start()


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
    parser = argparse.ArgumentParser("Listen to Slack Channels")
    parser.add_argument("workspace", action="store", help="Slack Workspace")
    args = parser.parse_args()
    init(args)


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
    try:
        main(args)
    except KeyboardInterrupt:
        pass
