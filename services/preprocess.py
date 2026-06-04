import cv2
import numpy as np


def decode_image(image_bytes: bytes):
    """
    Decode raw bytes menjadi numpy BGR array menggunakan OpenCV.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def preprocess_image(img: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
    """
    BGR → RGB → resize to target_size → float32 → /255.0 → expand dims
    """
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, target_size)
    img = img.astype("float32")
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    return img


def preprocess_mobilenet(img: np.ndarray) -> np.ndarray:
    """
    Preprocess gambar untuk input MobileNetV2 (backward compatibility).
    """
    return preprocess_image(img, (128, 128))
