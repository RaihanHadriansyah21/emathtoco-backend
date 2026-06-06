import cv2
import numpy as np

from utils.supabase_client import supabase


def check_file_exists(image_path: str) -> bool:
    """
    Cek apakah file ada di Supabase Storage bucket "lembar-jawaban".

    Return:
        True jika file ditemukan
        False jika file tidak ditemukan atau terjadi error
    """
    try:
        file_bytes = supabase.storage.from_("lembar-jawaban").download(image_path)
        return file_bytes is not None and len(file_bytes) > 0
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
    except Exception as e:
        raise FileNotFoundError(
            f"File tidak ditemukan di Storage: {image_path} — {str(e)}"
        )

    if file_bytes is None or len(file_bytes) == 0:
        raise FileNotFoundError(
            f"File kosong atau tidak ditemukan di Storage: {image_path}"
        )

    np_array = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image

