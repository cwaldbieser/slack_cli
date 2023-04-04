import subprocess
import tempfile

import httpx
from rich import inspect

image_types = frozenset(["image/jpeg", "image/png", "image/gif"])


def display_image(config, file_id):
    """
    Download and display an image.
    """
    user_token = config["oauth"]["user_token"]
    params = {"file": file_id}
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/files.info"
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return
    json_response = r.json()
    try:
        file_info = json_response["file"]
    except KeyError:
        inspect(json_response)
        raise
    private_url = file_info["url_private"]
    r = httpx.get(private_url, headers=headers)
    if r.status_code != 200:
        return
    with tempfile.NamedTemporaryFile(delete=False) as f:
        for data in r.iter_bytes():
            f.write(data)
        temp_name = f.name
        cmd = ("kitty", "+kitten", "icat", temp_name)
        subprocess.run(cmd)
