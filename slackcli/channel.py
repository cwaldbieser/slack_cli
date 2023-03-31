import httpx

channel_map_ = None


def get_channels(config):
    """
    Get channels.
    """
    global channel_map_
    url = "https://slack.com/api/conversations.list"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    response = httpx.get(url, headers=headers)
    json_response = response.json()
    channels = json_response["channels"]
    channel_map_ = {}
    for channel in channels:
        channel_id = channel["id"]
        channel_info = {}
        is_archived = channel["is_archived"]
        if is_archived:
            continue
        channel_info["name"] = channel["name"]
        channel_info["is_channel"] = channel["is_channel"]
        channel_info["is_group"] = channel["is_group"]
        channel_info["is_im"] = channel["is_im"]
        channel_info["is_mpim"] = channel["is_mpim"]
        channel_info["is_private"] = channel["is_private"]
        channel_map_[channel_id] = channel_info


def get_channel_info(channel_id):
    """
    Get channel info by channel ID.
    Returns None if channel ID cannot be determined.
    """
    global channel_map_
    return channel_map_[channel_id]


def get_channel_id_by_name(name):
    """
    Return the channel ID of the channel that matches `name`.
    """
    global channel_map_
    search_term = name.lower()
    for channel_id, info in channel_map_.items():
        channel_name = info["name"].lower()
        if channel_name == search_term:
            return channel_id
    return None