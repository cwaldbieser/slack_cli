#! /usr/bin/env python

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

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


def get_message_text_(args):
    """
    Get the message text.
    """
    text_parts = []
    args_text = args.message
    if args_text is not None:
        text_parts.append(args_text)
    if args.stdin:
        text = sys.stdin.read()
        text_parts.append(text)
    if args.visual:
        text = get_text_from_visual_editor_()
        if text is not None:
            text_parts.append(text)
    if len(text_parts) == 0:
        return None
    return "".join(text_parts)


def get_text_from_visual_editor_():
    """
    Launch a visual editor (like vim) and collect the text output from it as a
    message.
    """
    visual = os.environ.get("VISUAL")
    if visual is None:
        return None
    try:
        fd, tmp_path = tempfile.mkstemp()
        os.close(fd)
        subprocess.call([visual, tmp_path])
        with open(tmp_path, "r") as f:
            text = f.read()
            if len(text) == 0:
                return None
            return text
    finally:
        os.unlink(tmp_path)


def post_message(channel_id, args, config):
    """
    Post a text message to a channel.
    """
    text = get_message_text_(args)
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
    text = get_message_text_(args)
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
    parser.add_argument("--stdin", action="store_true", help="Read message from STDIN.")
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Compose message in an editor specified by the VISUAL environment variable.",
    )
    args = parser.parse_args()
    main(args)
