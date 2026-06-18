import cv2
import numpy as np

from utils.supabase_client import supabase


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

