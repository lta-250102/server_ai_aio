"""Services package.

Re-exports the Triton connection pool and the image-detection helper
so that external code can import from ``services`` directly.
"""

from .image_detection import detect_image
from .triton import get_triton_client, TritonClient
