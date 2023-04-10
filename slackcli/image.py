import subprocess
import tempfile


image_types = frozenset(["image/jpeg", "image/png", "image/gif"])


def display_image(file_data):
    """
    Display an image.
    """
    chunk_size = 1024
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
        while True:
            data = file_data.read(chunk_size)
            if data == b"":
                break
            f.write(data)
        f.flush()
        cmd = ("kitty", "+kitten", "icat", temp_name)
        subprocess.run(cmd)
