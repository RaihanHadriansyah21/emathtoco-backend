from utils.supabase_client import supabase


def get_answer_sheets(submission_id: str):

    response = (
        supabase.table("lembar_jawaban")
        .select("*")
        .eq("pengumpulan_tugas_id", submission_id)
        .execute()
    )

    return response.data
