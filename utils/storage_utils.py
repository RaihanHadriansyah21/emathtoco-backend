from utils.supabase_client import supabase


def download_image(storage_path: str):

    response = supabase.storage.from_("lembar-jawaban").download(storage_path)

    return response
