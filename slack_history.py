#! /usr/bin/env python

import argparse
import datetime
import sys

import httpx

from slackcli.channel import get_channel_id_by_name, load_channels
from slackcli.config import load_config
from slackcli.message import display_message_item
from slackcli.user import get_users


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config(args.workspace)
    load_channels(config)
    get_users(config)
    channel_id = get_channel_id_by_name(args.channel)
    if channel_id is None:
        print(f"Channel '{args.channel}' could not be found.")
        sys.exit(1)
    if args.pins:
        results = get_pins_for_channel(channel_id, config)
    else:
        results = get_history_for_channel(channel_id, args.days, config)
    for item in results:
        display_message_item(item, config, show_thread_id=args.show_thread_id)


def get_pins_for_channel(channel_id, config):
    """
    Get the pins for a channel.
    """
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/pins.list"
    params = {"channel": channel_id}
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when fetching"
            f" pins for channel with id {channel_id}.",
            file=sys.stderr,
        )
        return
    json_response = r.json()
    items = json_response["items"]
    for item in items:
        if item["type"] == "message":
            message = item["message"]
            yield message


def get_history_for_channel(channel_id, days, config):
    """
    Generator produces `days` days worth of history from the channel specified
    by channel ID.
    """
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/conversations.history"
    ts = (datetime.datetime.today() - datetime.timedelta(days)).timestamp()
    params = {"channel": channel_id, "limit": 100, "oldest": ts}
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when fetching"
            f" history for channel with id {channel_id}.",
            file=sys.stderr,
        )
        return
    json_response = r.json()
    messages = json_response["messages"]
    messages.reverse()
    for message in messages:
        yield message


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Display Slack history.")
    parser.add_argument(
        "workspace",
        action="store",
        help="Slack Workspace",
    )
    parser.add_argument(
        "channel",
        action="store",
        help="The name of the channel to display history from.",
    )
    parser.add_argument(
        "-d",
        "--days",
        default=1,
        type=int,
        help="The number of days worth of history to display.",
    )
    parser.add_argument(
        "-p",
        "--pins",
        action="store_true",
        help="Get posts pinned to the channel instead of normal history.",
    )
    parser.add_argument(
        "-t",
        "--show-thread-id",
        action="store_true",
        help="Show the thread ID of each post.",
    )
    args = parser.parse_args()
    main(args)
