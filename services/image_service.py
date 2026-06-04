import cv2
import numpy as np

from utils.supabase_client import supabase


def download_image(image_path: str) -> np.ndarray:
    """
    Download gambar dari Supabase Storage dan decode menjadi numpy BGR array.

    Parameter:
        image_path : storage path relatif, contoh:
                     "mahasiswa_id/submission_id/S-1A.jpeg"

    Return:
        numpy array shape (H, W, 3) dtype uint8, format BGR (OpenCV)
        None jika decode gagal
    """
    file_bytes = supabase.storage.from_("lembar-jawaban").download(image_path)
    np_array = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image
