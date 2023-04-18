import httpx
from rich import inspect

user_map_ = None


def load_users(config):
    """
    Get users.
    """
    global user_map_
    user_map_ = {}
    url = "https://slack.com/api/users.list"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    response = httpx.get(url, headers=headers)
    json_response = response.json()
    try:
        users = json_response["members"]
    except KeyError:
        inspect(json_response)
        raise
    for user in users:
        user_id = user["id"]
        deleted = user["deleted"]
        if deleted:
            continue
        user_info = {}
        user_info["name"] = user["name"]
        user_map_[user_id] = user_info


def get_all_users():
    """
    Generator yields (user_id, user_info).
    """
    for user_id, user_info in user_map_.items():
        yield user_id, user_info


def get_user_info(user_id):
    """
    Get the user name from the `user_id`.
    """
    global user_map_
    return user_map_.get(user_id)
