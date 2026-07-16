import cv2
import numpy as np


def decode_image(image_bytes: bytes):
    """
    Decode raw bytes menjadi numpy BGR array menggunakan OpenCV.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


DEFAULT_PREPROCESSING = "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255"
ANSWER_BOX_CROP_PREFIX = "ANSWER_BOX_CROP_THEN_"
ANSWER_BOX_OTSU_PREFIX = "ANSWER_BOX_CROP_OTSU_INVERTED_THEN_"
SECTION_BINARY_PREFIX = "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_"


def _to_section_binary_rgb(img: np.ndarray) -> np.ndarray:
    """
    Match the real Models_New training images.

    The verified Preprocessed_Dataset samples are single-channel binary PNGs:
    black ink (0) on a white background (255). Keras loaded those files with
    its default RGB color mode, so the runtime contract is the same binary
    image repeated across three RGB channels.

    The frontend already lets the student crop one complete section. Do not
    run contour-based cropping here because a second crop can remove the
    section label, border, margin, or handwriting that existed during
    training.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)


def _crop_answer_box(img: np.ndarray, padding: int = 12) -> np.ndarray:
    """
    Detect and crop the answer box while preserving the original BGR pixels.

    Legacy preprocessing retained for old manifests and rollback only.
    """
    original = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(
        closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    h_img, w_img = img.shape[:2]
    candidate_boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / max(h, 1)
        if w > 0.45 * w_img and h > 0.20 * h_img and aspect_ratio > 1.2:
            candidate_boxes.append((x, y, w, h, w * h))

    if candidate_boxes:
        x, y, w, h, _ = sorted(
            candidate_boxes,
            key=lambda box: box[4],
            reverse=True,
        )[0]
        x1 = max(0, x + padding)
        y1 = max(0, y + padding)
        x2 = min(w_img, x + w - padding)
        y2 = min(h_img, y + h - padding)
        cropped = original[y1:y2, x1:x2]
        if cropped.size == 0:
            cropped = original
    else:
        cropped = original

    return cropped


def _crop_answer_box_otsu_inverted(img: np.ndarray, padding: int = 12) -> np.ndarray:
    """
    Optional legacy/experimental BW preprocessing mode.

    Not used by the active Models_New manifest after model-team confirmation.
    Kept only so old experiments can still be reproduced without changing code.
    """
    cropped = _crop_answer_box(img, padding=padding)
    gray_cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    _, final_img = cv2.threshold(
        gray_cropped,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    return cv2.cvtColor(final_img, cv2.COLOR_GRAY2RGB)


def preprocess_image(
    img: np.ndarray,
    target_size: tuple[int, int],
    preprocessing: str = DEFAULT_PREPROCESSING,
) -> np.ndarray:
    """
    Decode-ready BGR → dataset transform → resize → model preprocessing.

    Model lama memakai pembagian /255. Model baru memakai preprocessing bawaan
    Keras application sesuai arsitektur saat training. Models_New additionally
    uses the verified binary non-inverted dataset contract and nearest-neighbor
    resize used by Keras ImageDataGenerator.
    """
    interpolation = cv2.INTER_LINEAR
    if preprocessing.startswith(SECTION_BINARY_PREFIX):
        img = _to_section_binary_rgb(img)
        preprocessing = preprocessing.removeprefix(SECTION_BINARY_PREFIX)
        interpolation = cv2.INTER_NEAREST
    elif preprocessing.startswith(ANSWER_BOX_CROP_PREFIX):
        img = cv2.cvtColor(_crop_answer_box(img), cv2.COLOR_BGR2RGB)
        preprocessing = preprocessing.removeprefix(ANSWER_BOX_CROP_PREFIX)
    elif preprocessing.startswith(ANSWER_BOX_OTSU_PREFIX):
        img = _crop_answer_box_otsu_inverted(img)
        preprocessing = preprocessing.removeprefix(ANSWER_BOX_OTSU_PREFIX)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, target_size, interpolation=interpolation)
    img = img.astype("float32")
    img = np.expand_dims(img, axis=0)

    if preprocessing == "KERAS_MOBILENETV2_PREPROCESS_INPUT":
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

        return preprocess_input(img)
    if preprocessing == "KERAS_DENSENET121_PREPROCESS_INPUT":
        from tensorflow.keras.applications.densenet import preprocess_input

        return preprocess_input(img)
    if preprocessing == "KERAS_INCEPTIONV3_PREPROCESS_INPUT":
        from tensorflow.keras.applications.inception_v3 import preprocess_input

        return preprocess_input(img)

    img = img / 255.0
    return img


def preprocess_mobilenet(img: np.ndarray) -> np.ndarray:
    """
    Preprocess gambar untuk input MobileNetV2 (backward compatibility).
    """
    return preprocess_image(img, (128, 128))
