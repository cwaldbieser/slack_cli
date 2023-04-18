import httpx

channel_map_ = None


def query_channels(config):
    """
    Generator queries channels and produces entries corresponding to each one.
    """
    url = "https://slack.com/api/conversations.list"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"types": "public_channel,private_channel"}
    response = httpx.get(url, headers=headers, params=params)
    json_response = response.json()
    channels = json_response["channels"]
    for channel in channels:
        yield channel


def load_dm_info(config, dm_id):
    """
    Loads and returns DM info for the DM channel identified by `dm_id`.
    """
    url = "https://slack.com/api/conversations.info"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"channel": dm_id}
    response = httpx.get(url, headers=headers, params=params)
    json_response = response.json()
    return json_response["channel"]


def load_channels(config):
    """
    Get channels.
    """
    global channel_map_
    channel_map_ = {}
    for channel in query_channels(config):
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


def get_all_channel_ids():
    """
    Return a frozenset of all channel IDs.
    """
    return frozenset(channel_map_.keys())


def get_channels_by_type(channel_type):
    """
    Generator produces tuples of (channel_id, channel_name).
    """
    global channel_map_
    for channel_id, channel_info in channel_map_.items():
        is_channel = channel_info["is_channel"]
        is_group = channel_info["is_group"]
        is_im = channel_info["is_im"]
        is_mpim = channel_info["is_mpim"]
        if channel_type == "channel" and is_channel:
            yield (channel_id, channel_info["name"])
        elif channel_type == "group" and is_group:
            yield (channel_id, channel_info["name"])
        elif channel_type == "im" and is_im:
            yield (channel_id, channel_info["name"])
        elif channel_type == "mpim" and is_mpim:
            yield (channel_id, channel_info["name"])
