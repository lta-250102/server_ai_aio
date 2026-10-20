from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
import numpy as np
import cv2
from .depends import get_triton_client
from services import detect_image


router = APIRouter(prefix="/yolo", tags=["yolo"])

@router.get("/health")
async def health_check(client = Depends(get_triton_client)):
    return {m: "healthy" if await client.is_model_ready(m) else "unhealthy" for m in ("yolo_det", "yolo_seg")}


@router.post("/detect")
async def detect(image: UploadFile = File(...), client = Depends(get_triton_client)):
    file_bytes = await image.read()
    orig = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
    output = await detect_image(orig, client=client)
    return Response(cv2.imencode(".jpg", output)[1].tobytes(), media_type="image/jpeg")

