#! /usr/bin/env python

import argparse
import pathlib
import sys

import httpx
from rich import inspect

from slackcli.channel import get_channel_id_by_name, load_channels
from slackcli.config import load_config


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config(args.workspace)
    load_channels(config)
    channel_id = get_channel_id_by_name(args.channel)
    if channel_id is None:
        print(f"Channel '{args.channel}' could not be found.")
        sys.exit(1)
    if args.file is not None:
        upload_and_share_file(channel_id, args, config)
    else:
        post_message(channel_id, args, config)


def post_message(channel_id, args, config):
    """
    Post a text message to a channel.
    """
    text = args.message
    url = "https://slack.com/api/chat.postMessage"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "channel": channel_id,
        "text": text,
    }
    if args.thread:
        params["thread_ts"] = args.thread
    r = httpx.post(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when posting"
            f" to channel with id {channel_id}.",
            file=sys.stderr,
        )
        return
    json_response = r.json()
    if "error" in json_response:
        inspect(json_response)


def upload_and_share_file(channel_id, args, config):
    """
    Upload a file and share it to a channel with an optional initial comment.
    """
    text = args.message
    kwargs = {}
    params = {
        "channels": channel_id,
    }
    if text:
        params["initial_comment"] = text
    if args.thread:
        params["thread_ts"] = args.thread
    if args.file:
        pth = pathlib.Path(args.file.name)
        filename = pth.name
        kwargs["files"] = {
            "file": args.file,
        }
        params["filename"] = filename
        params["title"] = filename
    url = "https://slack.com/api/files.upload"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    r = httpx.post(url, headers=headers, params=params, **kwargs)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when posting"
            f" to channel with id {channel_id}.",
            file=sys.stderr,
        )
        return
    json_response = r.json()
    if "error" in json_response:
        inspect(json_response)


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
        help="The name of the channel to which the post will be sent.",
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Message text to post.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("rb"),
        help="A file to post.",
    )
    parser.add_argument(
        "-t",
        "--thread",
        help="Post in thread THREAD.",
    )
    args = parser.parse_args()
    main(args)
