"""YOLO image-detection endpoints."""

import logging

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from routers.depends import get_triton_client
from services import detect_image

logger = logging.getLogger("pyapi")

router = APIRouter(prefix="/yolo", tags=["yolo"])


@router.post("/detect")
async def detect(
    image: UploadFile = File(...),
    client = Depends(get_triton_client),
) -> Response:
    """Run YOLO detection on the uploaded image.

    Returns a JPEG with bounding boxes drawn.
    """
    try:
        file_bytes = await image.read()
        orig = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
        output = await detect_image(orig, client=client)
        return Response(
            cv2.imencode(".jpg", output)[1].tobytes(),
            media_type="image/jpeg",
        )
    except Exception as exc:
        logger.error("yolo_detect_error", extra={"error": str(exc)}, exc_info=True)
        raise
