from io import BytesIO

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from utils.supabase_client import supabase

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 12_000
MAX_IMAGE_PIXELS = 40_000_000
JPEG_SIGNATURE = b"\xff\xd8\xff"


def check_file_exists(image_path: str) -> bool:
    """
    Cek apakah file ada di Supabase Storage bucket "lembar-jawaban".

    EGRESS FIX: Menggunakan storage.list() (metadata-only, zero-egress)
    bukan .download() (binary download penuh) agar tidak menghabiskan bandwidth
    hanya untuk mengecek keberadaan file.

    Return:
        True jika file ditemukan
        False jika file tidak ditemukan atau terjadi error
    """
    try:
        # Split path into folder and filename
        # image_path format: "user_id/submission_id/S-1A.jpg"
        parts = image_path.rsplit("/", 1)
        if len(parts) == 2:
            folder_path, filename = parts
        else:
            folder_path = ""
            filename = image_path

        # Use list() — metadata only, zero egress cost
        result = supabase.storage.from_("lembar-jawaban").list(
            folder_path,
            {"limit": 100, "offset": 0, "search": filename}
        )
        if result and isinstance(result, list):
            return any(f.get("name") == filename for f in result)
        return False
    except Exception:
        return False


def download_image(image_path: str) -> np.ndarray:
    """
    Download gambar dari Supabase Storage dan decode menjadi numpy BGR array.

    Parameter:
        image_path : storage path relatif, contoh:
                     "mahasiswa_id/submission_id/S-1A.jpeg"

    Return:
        numpy array shape (H, W, 3) dtype uint8, format BGR (OpenCV)
        None jika decode gagal

    Raise:
        FileNotFoundError jika file tidak ditemukan di Storage
    """
    try:
        file_bytes = supabase.storage.from_("lembar-jawaban").download(image_path)
    except Exception as exc:
        raise FileNotFoundError("image_object_unavailable") from exc

    if file_bytes is None or len(file_bytes) == 0:
        raise FileNotFoundError("image_object_empty")

    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("image_too_large")

    if not file_bytes.startswith(JPEG_SIGNATURE):
        raise ValueError("invalid_image_signature")

    try:
        with Image.open(BytesIO(file_bytes)) as inspected:
            if inspected.format != "JPEG":
                raise ValueError("invalid_image_format")
            width, height = inspected.size
            if (
                width <= 0
                or height <= 0
                or width > MAX_IMAGE_DIMENSION
                or height > MAX_IMAGE_DIMENSION
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise ValueError("unsafe_image_dimensions")
            inspected.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("invalid_image_data") from exc

    np_array = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("image_decode_failed")
    return image

