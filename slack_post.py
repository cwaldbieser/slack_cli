#! /usr/bin/env python

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
from textwrap import dedent

import httpx
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.completion import PathCompleter, WordCompleter
from prompt_toolkit.key_binding import KeyBindings

# from prompt_toolkit.key_binding.bindings.vi import vi_navigation_mode
from prompt_toolkit.styles import Style
from rich import inspect
from rich.markdown import Markdown
from rich.markup import escape

from slackcli.channel import get_channel_id_by_name, get_channels_by_type, load_channels
from slackcli.config import load_config
from slackcli.console import console
from slackcli.user import get_all_users, load_users

RESULT_QUIT = 0
RESULT_HELP = 1
RESULT_MULTILINE = 2
RESULT_FILE = 3
RESULT_CHANNEL_SWITCH = 4
RESULT_DM_SWITCH = 5

style = Style.from_dict(
    {
        "bottom-toolbar": "#ffffff bg:#333333",
    }
)

bindings = KeyBindings()
stop_bindings = KeyBindings()


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config(args.workspace)
    load_channels(config)
    load_users(config)
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
        channel_type = tbconfig["channel_type"]
        multiline = tbconfig["multiline"]
        if channel_type == "dm":
            channel_type_label = "DM"
        else:
            channel_type_label = "channel"
        toolbar = [
            (
                "class:bottom-toolbar",
                f"multiline: {multiline}  {channel_type_label}: {channel_name}",
            )
        ]
        return toolbar

    return bottom_toolbar


@bindings.add("c-d")
def handle_ctrl_d(event):
    """
    Handle CTRL-D by exiting.
    """
    event.app.exit(RESULT_QUIT)


@bindings.add("c-c")
def handle_ctrl_c(event):
    """
    Handle CTRL-C by exiting.
    """
    event.app.exit(RESULT_QUIT)


@bindings.add("<sigint>")
def handle_sigint(event):
    """
    Handle CTRL-C by exiting.
    """
    event.app.exit(RESULT_QUIT)


@bindings.add("f1")
def handle_help(event):
    """
    Handle Help.
    """
    event.app.exit(RESULT_HELP)


@bindings.add("f2")
def handle_multiline(event):
    """
    Handle toggline multiline mode.
    """
    event.app.exit(RESULT_MULTILINE)


@bindings.add("f3")
def handle_file(event):
    """
    Handle uploading a file.
    """
    event.app.exit(RESULT_FILE)


@bindings.add("f4")
def handle_change_channel(event):
    """
    Handle changing the channel.
    """
    event.app.exit(RESULT_CHANNEL_SWITCH)


@bindings.add("f16")
def handle_change_dm(event):
    """
    Handle changing the DM.
    """
    event.app.exit(RESULT_DM_SWITCH)


@bindings.add("f6")
def handle_debug(event):
    """
    Handle debugging.
    """

    def debug_events_():
        inspect(event)
        buffer = event.current_buffer
        inspect(buffer)

    run_in_terminal(debug_events_)


@stop_bindings.add("c-c")
def handle_file_ctrl_c(event):
    """
    Handle CTRL-C by exiting the prompt.
    """
    event.app.exit("")


@stop_bindings.add("c-d")
def handle_file_ctrl_d(event):
    """
    Handle CTRL-D by exiting the prompt.
    """
    event.app.exit("")


def make_channel_completer():
    """
    Create a channel completer.
    """
    channel_map = {
        channel_name: channel_id
        for (channel_id, channel_name) in get_channels_by_type("channel")
    }
    completer = WordCompleter(channel_map.keys(), ignore_case=True)
    return completer, channel_map


def make_dm_completer():
    """
    Create a DM completer.
    """
    user_map = {
        channel_info["name"]: channel_id
        for (channel_id, channel_info) in get_all_users()
    }
    completer = WordCompleter(user_map.keys(), ignore_case=True)
    return completer, user_map


def print_repl_header():
    """
    Print the REPL header.
    """
    markdown = dedent(
        """\
    # Post Messages to Slack

    - F1 for help
    - CTRL-D to exit
    """
    )
    md = Markdown(markdown)
    console.print(md)
    console.print("")


def print_repl_help():
    """
    Print REPL help.
    """
    markdown = dedent(
        """\
    # Help for Posting Messages to Slack REPL

    Type messages at the prompt using vi bindings.
    In multiline mode, you must type ESC-ENTER to post a message.

    The following special keys and key combinations are available:

    - F1 this help.
    - F2 to toggle multi-line mode.
    - F3 to upload a file.
    - F4 to switch channels.
    - F16 to switch DMs.
    - CTRL-C or CTRL-D to exit

    In vi *normal mode* use common vi bindings:

    - Movements like `w`, `e`, `b`.
    - Beginning and end of line `0` and `$`.
    - Edit text in editor specified in `$EDITOR` by pressing `v`.
    """
    )
    md = Markdown(markdown)
    console.print(md)
    console.print("")


def do_repl(channel_id, args, config):
    """
    Accept messages from a prompt in a loop.
    vi bindings are used by default.
    An editor can be launched by "v" in normal mode.
    """
    global style
    multiline = False
    channel_name = args.channel
    tbconfig = {
        "channel_name": channel_name,
        "multiline": multiline,
        "channel_type": "channel",
    }
    bottom_toolbar = make_toolbar_func(tbconfig)
    print_repl_header()
    session = PromptSession(
        "message > ",
        vi_mode=True,
        multiline=multiline,
        prompt_continuation="> ",
        enable_open_in_editor=True,
        bottom_toolbar=bottom_toolbar,
        style=style,
        key_bindings=bindings,
    )
    file_session = PromptSession(
        "file > ",
        vi_mode=True,
        completer=PathCompleter(expanduser=True),
        key_bindings=stop_bindings,
    )
    channel_completer, channel_id_map = make_channel_completer()
    channel_session = PromptSession(
        "channel > ",
        vi_mode=True,
        completer=channel_completer,
        key_bindings=stop_bindings,
    )
    dm_completer, dm_id_map = make_dm_completer()
    dm_session = PromptSession(
        "user > ",
        vi_mode=True,
        completer=dm_completer,
        key_bindings=stop_bindings,
    )
    text = ""
    while True:
        result = session.prompt(default=text, multiline=multiline)
        text = ""
        if result == "":
            break
        elif result == RESULT_QUIT:
            break
        elif result == RESULT_HELP:
            buffer = session.default_buffer
            text = buffer.text
            print_repl_help()
            continue
        elif result == RESULT_CHANNEL_SWITCH:
            buffer = session.default_buffer
            text = buffer.text
            channel_type = tbconfig["channel_type"]
            if channel_type == "channel":
                kwargs = {"default": channel_name}
            else:
                kwargs = {}
            channel_result = channel_session.prompt(**kwargs)
            validate_result = validate_channel(
                channel_result, channel_id_map, default=(channel_id, channel_name)
            )
            if validate_result is None:
                continue
            channel_id, channel_name = validate_result
            tbconfig["channel_name"] = channel_name
            tbconfig["channel_type"] = "channel"
            continue
        elif result == RESULT_DM_SWITCH:
            buffer = session.default_buffer
            text = buffer.text
            channel_type = tbconfig["channel_type"]
            if channel_type == "dm":
                kwargs = {"default": channel_name}
            else:
                kwargs = {}
            dm_result = dm_session.prompt(**kwargs)
            validate_result = validate_dm(
                dm_result, dm_id_map, default=(channel_id, channel_name)
            )
            if validate_result is None:
                continue
            channel_id, channel_name = validate_result
            tbconfig["channel_name"] = channel_name
            tbconfig["channel_type"] = "dm"
            continue
        elif result == RESULT_MULTILINE:
            buffer = session.default_buffer
            text = buffer.text
            multiline = tbconfig["multiline"]
            multiline = not multiline
            tbconfig["multiline"] = multiline
            continue
        elif result == RESULT_FILE:
            buffer = session.default_buffer
            text = buffer.text
            file_result = file_session.prompt()
            validate_and_share_file(channel_id, config, file_result)
            continue
        post_message(channel_id, args, config, result)


def validate_channel(channel_name, channel_id_map, default=None):
    """
    Validate a channel name and return
    """
    channel_id = channel_id_map.get(channel_name)
    if channel_id is None:
        return default
    return channel_id, channel_name


def validate_dm(user_name, user_id_map, default=None):
    """
    Validate a user name and return
    """
    user_id = user_id_map.get(user_name)
    if user_id is None:
        return default
    return user_id, user_name


def validate_and_share_file(channel_id, config, path):
    """
    Validate and share a file.
    """
    if path == "":
        return
    pathobj = pathlib.Path(path).expanduser()
    if not pathobj.is_file():
        console.print(
            f"[error]ERROR:[/error] '[file]{escape(path)}[/file]' is not a file."
        )
        return
    with open(pathobj, "rb") as f:
        upload_and_share_file_impl_(channel_id, config, f)


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
    upload_and_share_file_impl_(
        channel_id, config, args.file, thread_ts=args.thread, initial_comment=text
    )


def upload_and_share_file_impl_(
    channel_id, config, fileobj, thread_ts=None, initial_comment=None
):
    """
    Implemention for uploading and sharing a file.
    """
    kwargs = {}
    params = {
        "channels": channel_id,
    }
    if initial_comment is not None:
        params["initial_comment"] = initial_comment
    if thread_ts is not None:
        params["thread_ts"] = thread_ts
    pth = pathlib.Path(fileobj.name)
    filename = pth.name
    kwargs["files"] = {
        "file": fileobj,
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
