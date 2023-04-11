import datetime

from rich import inspect
from rich.markup import escape

from slackcli.console import console
from slackcli.filecache import get_file
from slackcli.image import display_image, image_types
from slackcli.user import get_user_info


def display_message_item(item, config, filecache, show_thread_id=False, no_files=False):
    """
    Display a history item.
    """
    global style
    item_type = item["type"]
    if item_type != "message":
        return
    try:
        user_id = item["user"]
    except KeyError:
        inspect(item)
        raise
    user_info = get_user_info(user_id)
    if user_info is None:
        user_name = user_id
    else:
        user_name = user_info["name"]
    ts = item["ts"]
    dt = datetime.datetime.fromtimestamp(float(ts))
    fts = dt.strftime("%Y-%m-%d %H:%M:%S")
    ftext = format_text_item(item)
    user_part = rf"[user]\[{escape(user_name)}][/user]"
    ts_part = rf"[ts]\[{escape(fts)}][/ts]"
    parts = [user_part, ts_part]
    if show_thread_id:
        parts.append(rf"[thread]\[{escape(ts)}][/thread]")
    parts.append(ftext)
    message = " ".join(parts)
    console.print(message)
    if no_files:
        return
    files = item.get("files", [])
    for file_info in files:
        is_external = file_info.get("is_external", False)
        if is_external:
            link = escape(file_info["permalink_public"])
            name = escape(file_info["name"])
            console.print(f"[hyperlink][link={link}]{name} ({link})[/link][/hyperlink]")
            continue
        file_data = get_file(filecache, config, file_info)
        if file_data is None:
            continue
        name = file_info["name"]
        mimetype = file_info["mimetype"]
        if mimetype in image_types:
            display_image(file_data)
            console.print(f"[file]{escape(name)}[/file]")
        else:
            file_id = file_info["id"]
            console.print(f"[file]{escape(name)} (file ID: {escape(file_id)})[/file]")


def format_text_item(item):
    """
    Format a Slack text item.
    Return the formatted text.
    """
    parts = []
    blocks = item.get("blocks", [])
    for block in blocks:
        outer_elements = block["elements"]
        for outer_element in outer_elements:
            inner_elements = outer_element["elements"]
            for inner_element in inner_elements:
                elm_type = inner_element["type"]
                if elm_type == "text":
                    parts.append(escape(inner_element["text"]))
                elif elm_type == "link":
                    try:
                        link = inner_element["url"]
                    except KeyError:
                        inspect(inner_element)
                        raise
                    text = inner_element.get("text", link)
                    link = escape(link)
                    text = escape(text)
                    markup = (
                        f"[hyperlink][link={link}]{text} ({link})[/link][/hyperlink]"
                    )
                    parts.append(markup)
                elif elm_type == "emoji":
                    emoji = construct_emoji(inner_element)
                    parts.append(emoji)
    return "".join(parts)


def construct_emoji(element):
    """
    Construct an emoji from `element`.
    """
    unicode_hex = element["unicode"]
    hexes = unicode_hex.split("-")
    parts = [chr(int(code, 16)) for code in hexes]
    return "".join(parts)
