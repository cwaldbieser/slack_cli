import contextlib
import os
import tempfile

import chafa
from chafa.loader import Loader

image_types = frozenset(["image/jpeg", "image/png", "image/gif"])


def display_image(file_data):
    """
    Display an image.
    """
    FONT_HEIGHT = 24
    FONT_WIDTH = 11
    with write_image_data_to_temp_file_(file_data) as f:
        image_path = f.name
        # Load image
        image = Loader(image_path)
    # Create config
    config = chafa.CanvasConfig()
    # Detect pixel mode to use.
    configure_pixel_mode_(config)
    # Set geometry
    config.height = 40
    config.width = 40
    config.calc_canvas_geometry(image.width, image.height, FONT_WIDTH / FONT_HEIGHT)
    config.cell_width = FONT_WIDTH
    config.cell_height = FONT_HEIGHT
    # Configure the canvas.
    canvas = chafa.Canvas(config)
    # Produce the image output.
    canvas.draw_all_pixels(
        image.pixel_type, image.get_pixels(), image.width, image.height, image.rowstride
    )
    output = canvas.print(fallback=True)
    print(output.decode())


def configure_pixel_mode_(config):
    """
    Configure pixel mode.
    """
    if os.environ.get("TERM") == "xterm-kitty":
        config.pixel_mode = chafa.PixelMode.CHAFA_PIXEL_MODE_KITTY
    else:
        db = chafa.TermDb()
        terminfo = db.detect()
        term_caps = terminfo.detect_capabilities()
        config.pixel_mode = term_caps.pixel_mode
        config.canvas_mode = term_caps.canvas_mode


@contextlib.contextmanager
def write_image_data_to_temp_file_(file_data):
    """
    Writes image data to temporary file.
    """
    chunk_size = 1024
    with tempfile.NamedTemporaryFile(delete=True) as f:
        # temp_name = f.name
        while True:
            data = file_data.read(chunk_size)
            if data == b"":
                break
            f.write(data)
        f.flush()
        yield f
