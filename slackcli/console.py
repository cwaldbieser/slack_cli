from rich.console import Console
from rich.theme import Theme

custom_theme = Theme(
    {
        "channel": "white on #9370DB",
        "user": "#32CD32 bold",
        "image": "cyan underline",
        "file": "white underline",
        "ts": "purple",
        "thread": "white italic",
        "hyperlink": "blue bold",
    }
)
console = Console(theme=custom_theme)
