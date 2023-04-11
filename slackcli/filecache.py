import datetime
import pathlib
import sqlite3
from contextlib import contextmanager
from io import BytesIO

import httpx
from rich import inspect


@contextmanager
def init_filecache(workspace):
    """
    Make sure file cache has been initialized for this workspace.
    """
    cache_file = pathlib.Path(f"~/.slackcli/{workspace}.db").expanduser()
    with sqlite3.connect(cache_file) as db:
        create_tables_(db)
        yield db


def create_tables_(db):
    """
    Create file cache tables.
    """
    cur = db.cursor()
    sql = """\
          CREATE TABLE IF NOT EXISTS files(file_id TEXT PRIMARY KEY,
            cached NUMERIC, name TEXT, mimetype TEXT, title TEXT, file_data BLOB)
          """
    cur.execute(sql)
    db.commit()


def insert_file_in_cache(db, file_id, binary_data, name, mimetype, title=None):
    """
    Inserts the file into the cache.
    """
    if title is None:
        title = name
    cached = datetime.datetime.today().timestamp()
    sql = """\
          REPLACE INTO files(file_id, cached, name, mimetype, title, file_data)
          VALUES (?, ?, ?, ?, ?, ?)
          """
    cur = db.cursor()
    cur.execute(sql, [file_id, cached, name, mimetype, title, binary_data])
    db.commit()
    return BytesIO(binary_data)


def get_file_from_cache(db, file_id, timestamp=None):
    """
    Return file data for the file ID in the cache.
    If ``timestamp`` is provided, only return file data that matches the
    timestamp or is more recent.
    Returns None if no file data is cached.
    """
    cur = db.cursor()
    sql = """\
          SELECT cached,
                 file_data
          FROM files
          WHERE file_id = ?
          """
    cur.execute(sql, [file_id])
    row = cur.fetchone()
    if row is None:
        return None
    cached, file_data = row
    if timestamp is not None:
        if cached < timestamp:
            return None
    return BytesIO(file_data)


def get_file(db, config, file_info):
    """
    Return binary file data or None if file cannot be retrieved.
    """
    user_token = config["oauth"]["user_token"]
    file_id = file_info["id"]
    is_tombstone = file_info.get("mode") == "tombstone"
    if is_tombstone:
        return get_file_from_cache(db, file_id)
    params = {"file": file_id}
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/files.info"
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return get_file_from_cache(db, file_id)
    json_response = r.json()
    try:
        file_metadata = json_response["file"]
    except KeyError:
        inspect(json_response)
        raise
    timestamp = file_metadata["created"]
    file_data = get_file_from_cache(db, file_id, timestamp=timestamp)
    if file_data is not None:
        return file_data
    private_url = file_metadata["url_private"]
    r = httpx.get(private_url, headers=headers)
    if r.status_code != 200:
        return None
    name = file_metadata["name"]
    mimetype = file_metadata["mimetype"]
    title = file_metadata.get("title")
    file_data = insert_file_in_cache(
        db, file_id, r.content, name, mimetype, title=title
    )
    return file_data
