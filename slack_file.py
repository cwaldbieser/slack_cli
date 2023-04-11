#! /usr/bin/env python

import argparse
import datetime

from dateutil.tz import tzlocal
from rich.table import Table

from slackcli.console import console
from slackcli.filecache import get_file_info, init_filecache


def handle_list_command(filecache, args):
    """
    List files in the file cache.
    """
    table = Table(title="Cached files")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Cached", style="white", no_wrap=True)
    table.add_column("Name", style="blue", no_wrap=True)
    table.add_column("MimeType", style="white", no_wrap=True)
    table.add_column("Title", style="white", no_wrap=True)
    local_tz = tzlocal()
    for row in get_file_info(filecache):
        file_id, cached, name, mimetype, title = row
        dt_utc = datetime.datetime.fromtimestamp(cached)
        dt_local_tz = dt_utc.astimezone(local_tz)
        date_str = dt_local_tz.isoformat()
        table.add_row(file_id, date_str, name, mimetype, title)
    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Manipulate cached Slack files.")
    parser.add_argument(
        "workspace",
        action="store",
        help="Slack Workspace",
    )
    subparsers = parser.add_subparsers(help="sub-command help")
    parser_list = subparsers.add_parser("list", help="List cached file information.")
    # parser_list.add_argument("bar", type=int, help="bar help")
    parser_list.set_defaults(dispatcher=handle_list_command)
    args = parser.parse_args()
    with init_filecache(args.workspace) as filecache:
        args.dispatcher(filecache, args)
