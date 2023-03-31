#! /usr/bin/env python

import argparse

# from rich import inspect
from rich.table import Table

from slackcli.channel import query_channels
from slackcli.config import load_config
from slackcli.console import console


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config(args.workspace)
    table = Table(title="Slack Channels")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="blue", no_wrap=True)
    table.add_column("is_group", style="white", no_wrap=True)
    table.add_column("is_im", style="white", no_wrap=True)
    table.add_column("is_mpim", style="white", no_wrap=True)
    table.add_column("is_private", style="white", no_wrap=True)
    table.add_column("is_archived", style="white", no_wrap=True)
    for entry in query_channels(config):
        table.add_row(
            entry["id"],
            entry["name"],
            str(entry["is_group"]),
            str(entry["is_im"]),
            str(entry["is_mpim"]),
            str(entry["is_private"]),
            str(entry["is_archived"]),
        )
    console.print(table)


def display_channel(entry):
    """
    Display an individual channel.
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Get information about Slack channels.")
    parser.add_argument(
        "workspace",
        action="store",
        help="Slack Workspace",
    )
    args = parser.parse_args()
    main(args)
