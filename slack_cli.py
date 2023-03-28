#! /usr/bin/env python

import pathlib
import re

import logzero
import toml
from logzero import logger
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = None


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
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    SocketModeHandler(app, app_token).start()


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
    message = context["matches"][0]
    logger.info(f"Message: {message}")
    logger.debug(context)


# @app.event("message")
# def handle_message_events(body, logger):
#     print(body)


# Start your app
if __name__ == "__main__":
    main()
