from rich.console import Console
from rich.theme import Theme

custom_theme = Theme(
    {
        "channel": "white on #9370DB",
        "error": "white on red",
        "file": "white underline",
        "hyperlink": "blue bold",
        "image": "cyan underline",
        "thread": "white italic",
        "ts": "purple",
        "user": "#32CD32 bold",
    }
)
console = Console(theme=custom_theme)
