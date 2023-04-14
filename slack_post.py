#! /usr/bin/env python

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

import httpx
from prompt_toolkit import prompt

# from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import radiolist_dialog

# from prompt_toolkit.key_binding.bindings.vi import vi_navigation_mode
from prompt_toolkit.styles import Style
from rich import inspect

from slackcli.channel import get_channel_id_by_name, get_channels_by_type, load_channels
from slackcli.config import load_config

style = Style.from_dict(
    {
        "bottom-toolbar": "#ffffff bg:#333333",
    }
)

bindings = KeyBindings()


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
    if args.repl:
        do_repl(channel_id, args, config)
    elif args.file is not None:
        upload_and_share_file(channel_id, args, config)
    else:
        text = get_message_text_(args)
        post_message(channel_id, args, config, text)


def make_toolbar_func(tbconfig):
    """
    Make a toolbar function.
    """

    def bottom_toolbar():
        channel_name = tbconfig["channel_name"]
        return [("class:bottom-toolbar", f" channel: {channel_name}")]

    return bottom_toolbar


@bindings.add("c-d")
def handle_ctrl_d(event):
    """
    Handle CTRL-D by exiting.
    """
    event.app.exit(0)


@bindings.add("c-c")
def handle_ctrl_c(event):
    """
    Handle CTRL-C by exiting.
    """
    event.app.exit(0)


@bindings.add("<sigint>")
def handle_sigint(event):
    """
    Handle CTRL-C by exiting.
    """
    event.app.exit(0)


@bindings.add("f1")
def handle_change_channel(event):
    """
    Handle changing the channel.
    """
    event.app.exit(1)


def select_channel_name(default_channel_id):
    """
    Allow current channel to be selected interactively.
    """
    channels = {
        channel_id: channel_name
        for (channel_id, channel_name) in get_channels_by_type("channel")
    }
    values = list(channels.items())
    values.sort(key=lambda x: x[1])
    channel_id = radiolist_dialog(
        title="Channels",
        text="Choose a channel.",
        values=values,
        default=default_channel_id,
    ).run()
    if channel_id is None:
        channel_id = default_channel_id
    return channel_id, channels[channel_id]


def do_repl(channel_id, args, config):
    """
    Accept messages from a prompt in a loop.
    vi bindings are used by default.
    An editor can be launched by "v" in normal mode.
    """
    global style
    tbconfig = {"channel_name": args.channel}
    bottom_toolbar = make_toolbar_func(tbconfig)
    result_quit = 0
    result_channel_switch = 1
    while True:
        result = prompt(
            "message > ",
            vi_mode=True,
            multiline=True,
            prompt_continuation="> ",
            enable_open_in_editor=True,
            bottom_toolbar=bottom_toolbar,
            style=style,
            key_bindings=bindings,
        )
        if result == "":
            break
        elif result == result_quit:
            break
        elif result == result_channel_switch:
            channel_id, channel_name = select_channel_name(channel_id)
            tbconfig["channel_name"] = channel_name
            continue
        post_message(channel_id, args, config, result)


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
        text = prompt(
            "message > ",
            vi_mode=True,
            multiline=True,
            prompt_continuation="> ",
            enable_open_in_editor=True,
        )
        text_parts.append(text)
    if args.code:
        text_parts.append("```")
        text_parts.insert(0, "```")
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


def post_message(channel_id, args, config, text):
    """
    Post a text message to a channel.
    """
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
        "-c",
        "--code",
        action="store_true",
        help="Wrap message text in Slack code mrkdwn.",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Compose message in an editor specified by the VISUAL environment variable.",
    )
    parser.add_argument(
        "-r",
        "--repl",
        action="store_true",
        help="Compose messages using a Read-Eval-Print Loop.",
    )
    args = parser.parse_args()
    main(args)
