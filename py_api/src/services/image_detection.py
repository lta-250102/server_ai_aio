import logging
import tritonclient.grpc.aio as grpcclient
import numpy as np
import cv2


logger = logging.getLogger("pyapi")
CLASS_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    4: "airplane", 5: "bus", 6: "train", 7: "truck",
    8: "boat", 9: "traffic light", 10: "fire hydrant",
    11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse",
    18: "sheep", 19: "cow", 20: "elephant", 21: "bear",
    22: "zebra", 23: "giraffe", 24: "backpack", 25: "umbrella",
    26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball",
    33: "kite", 34: "baseball bat", 35: "baseball glove",
    36: "skateboard", 37: "surfboard", 38: "tennis racket",
    39: "bottle", 40: "wine glass", 41: "cup", 42: "fork",
    43: "knife", 44: "spoon", 45: "bowl", 46: "banana",
    47: "apple", 48: "sandwich", 49: "orange", 50: "broccoli",
    51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut",
    55: "cake", 56: "chair", 57: "couch", 58: "potted plant",
    59: "bed", 60: "dining table", 61: "toilet", 62: "tv",
    63: "laptop", 64: "mouse", 65: "remote", 66: "keyboard",
    67: "cell phone", 68: "microwave", 69: "oven", 70: "toaster",
    71: "sink", 72: "refrigerator", 73: "book", 74: "clock",
    75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
    79: "toothbrush",
}

_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 128), (0, 128, 128),
    (128, 128, 0), (128, 0, 0),
]

IMG_SIZE = 640


def _letterbox(image: np.ndarray, new_size: int = 640) -> tuple[np.ndarray, float, tuple]:
    """Letterbox: giữ tỷ lệ, thêm padding. Trả về (tensor, scale, padding).
    
    Input/Output: toàn bộ xử lý trên numpy RGB array, không dùng PIL.
    """
    orig_h, orig_w = image.shape[:2]
    ratio = min(new_size / orig_w, new_size / orig_h)
    new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    # Tạo ảnh trắng padding (RGB)
    padded = np.full((new_size, new_size, 3), 128, dtype=np.uint8)
    pad_x, pad_y = (new_size - new_w) // 2, (new_size - new_h) // 2
    padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
    arr = padded.astype(np.float32) / 255.0
    tensor = np.expand_dims(np.transpose(arr, (2, 0, 1)), 0)
    return tensor, ratio, (pad_x, pad_y)


def _draw_boxes(image: np.ndarray, detections: np.ndarray, orig_size: tuple, ratio: float, padding: tuple, conf_th: float = 0.25) -> np.ndarray:
    """Vẽ boxes, scale tọa độ từ 640×640 về ảnh gốc (letterbox).
    
    Image input/output: numpy RGB array.
    """
    img = image.copy()
    pad_x, pad_y = padding
    detections = np.squeeze(detections, axis=0)
    for row in detections:
        x1, y1, x2, y2, conf, cls_id = row[:6]
        if conf < conf_th:
            continue
        # Scale tọa độ: bỏ padding → chia ratio → về ảnh gốc
        x1 = (x1 - pad_x) / ratio
        y1 = (y1 - pad_y) / ratio
        x2 = (x2 - pad_x) / ratio
        y2 = (y2 - pad_y) / ratio
        cls_id = int(cls_id)
        # Màu RGB
        color = _COLORS[cls_id % len(_COLORS)]
        label = f"{CLASS_NAMES.get(cls_id, cls_id)} {conf:.2f}"
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        tw, th = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        cv2.rectangle(img, (int(x1), int(y1) - th - 6), (int(x1) + tw, int(y1) + 4), color, -1)
        cv2.putText(img, label, (int(x1), int(y1) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return img


async def detect_image(orig: np.ndarray, client: grpcclient.InferenceServerClient) -> np.ndarray:
    """Detect objects in a RGB numpy array. Returns RGB numpy array with boxes drawn."""
    h, w = orig.shape[:2]
    tensor, ratio, padding = _letterbox(orig)
    inputs = [grpcclient.InferInput("images", tensor.shape, "FP32")]
    inputs[0].set_data_from_numpy(tensor)
    outputs = [grpcclient.InferRequestedOutput("output0")]
    resp = await client.infer(model_name="yolo_det", inputs=inputs, outputs=outputs)
    detections = resp.as_numpy("output0")
    result = _draw_boxes(orig, detections, (w, h), ratio, padding)
    # Count detected boxes
    detections = np.squeeze(detections, axis=0)
    num_detections = sum(1 for row in detections if row[5] >= 0.25)
    logger.info("yolo_detect_infer", extra={"image_size": f"{w}x{h}", "detections": num_detections})
    return result
