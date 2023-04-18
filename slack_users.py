#! /usr/bin/env python

import argparse

# from rich import inspect
from rich.table import Table

from slackcli.config import load_config
from slackcli.console import console
from slackcli.user import get_all_users, load_users


def main(args):
    """
    The main program entrypoint.
    """
    config = load_config(args.workspace)
    load_users(config)
    table = Table(title="Slack Users")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="blue", no_wrap=True)
    table.add_column("is_admin", style="white", no_wrap=True)
    table.add_column("is_bot", style="white", no_wrap=True)
    table.add_column("is_owner", style="white", no_wrap=True)
    table.add_column("is_primary_owner", style="white", no_wrap=True)
    table.add_column("tz", style="white", no_wrap=True)
    for user_id, entry in get_all_users():
        table.add_row(
            user_id,
            entry["name"],
            str(entry["is_admin"]),
            str(entry["is_bot"]),
            str(entry["is_owner"]),
            str(entry["is_primary_owner"]),
            str(entry["tz"]),
        )
    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Get information about Slack users.")
    parser.add_argument(
        "workspace",
        action="store",
        help="Slack Workspace",
    )
    args = parser.parse_args()
    main(args)
