import pathlib

import toml


def load_config(workspace):
    """
    Load config.
    """
    pth = pathlib.Path(f"~/.slackcli/{workspace}.toml").expanduser()
    with open(pth, "r") as f:
        config = toml.load(f)
    return config
