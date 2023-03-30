import pathlib

import toml


def load_config():
    """
    Load config.
    """
    pth = pathlib.Path("~/.slackcli/waldbiec-dev.toml").expanduser()
    with open(pth, "r") as f:
        config = toml.load(f)
    return config
