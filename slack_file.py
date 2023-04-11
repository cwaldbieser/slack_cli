#! /usr/bin/env python

import argparse
import datetime
import sys

from dateutil.tz import tzlocal
from rich.table import Table

from slackcli.console import console
from slackcli.filecache import get_file_from_cache, get_file_info, init_filecache


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


def handle_copy_command(filecache, args):
    """
    Copy cached files to the filesystem.
    """
    file_id = args.file_id
    file_path = args.filename
    file_data = get_file_from_cache(filecache, file_id)
    if file_data is None:
        print(f"Could not retrieve file with ID {file_id}.", file=sys.stderr)
        sys.exit(1)
    with open(file_path, "wb") as f:
        f.write(file_data.read())


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Manipulate cached Slack files.")
    parser.add_argument(
        "workspace",
        action="store",
        help="Slack Workspace",
    )
    subparsers = parser.add_subparsers(help="sub-command help")
    parser_list = subparsers.add_parser(
        "list", aliases=["ls"], help="List cached file information."
    )
    parser_list.set_defaults(dispatcher=handle_list_command)
    parser_copy = subparsers.add_parser(
        "copy", aliases=["cp"], help="Copy file from cache to filesystem."
    )
    parser_copy.add_argument("file_id", help="The ID of the file to copy.")
    parser_copy.add_argument("filename", help="Copy cached file to FILENAME.")
    parser_copy.set_defaults(dispatcher=handle_copy_command)
    args = parser.parse_args()
    with init_filecache(args.workspace) as filecache:
        args.dispatcher(filecache, args)
