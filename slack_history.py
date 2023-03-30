#! /usr/bin/env python

import argparse
import datetime
import sys

import httpx
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from slackcli.channel import get_channel_id_by_name, get_channels
from slackcli.config import load_config
from slackcli.image import display_image, image_types
from slackcli.user import get_user_info, get_users

style = Style.from_dict(
    {
        "channel": "bg:#9370DB fg:white bold",
        "user": "fg:#32CD32 underline",
        "image": "fg:cyan underline",
        "file": "fg:white underline",
        "ts": "fg:purple",
    }
)


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config()
    get_channels(config)
    get_users(config)
    channel_id = get_channel_id_by_name(args.channel)
    if channel_id is None:
        print(f"Channel '{args.channel}' could not be found.")
        sys.exit(1)
    for item in get_history_for_channel(channel_id, args.days, config):
        display_history_item(item, config)


def display_history_item(item, config):
    """
    Display a history item.
    """
    global style
    item_type = item["type"]
    if item_type != "message":
        return
    user_id = item["user"]
    user_info = get_user_info(user_id)
    if user_info is None:
        user_name = user_id
    else:
        user_name = user_info["name"]
    ts = item["ts"]
    dt = datetime.datetime.fromtimestamp(float(ts))
    fts = dt.strftime("%Y-%m-%d %H:%M:%S")
    text = item["text"]
    ftext = FormattedText(
        [
            ("class:user", f"[{user_name}]"),
            ("class:ts", f"[{fts}]"),
            ("", " "),
            ("", text),
        ]
    )
    print_formatted_text(ftext, style=style)
    files = item.get("files", [])
    for file_info in files:
        file_id = file_info["id"]
        file_mode = file_info["mode"]
        if file_mode == "tombstone":
            continue
        name = file_info["name"]
        mimetype = file_info["mimetype"]
        if mimetype in image_types:
            display_image(config, file_id)
        ftext = FormattedText([("class:file", name)])
        print_formatted_text(ftext, style=style)


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
    args = parser.parse_args()
    main(args)
