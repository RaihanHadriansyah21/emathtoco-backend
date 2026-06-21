CLASS_SCORE_MAP: dict[str, list[int]] = {
    # S-1A: Skor dimulai dari 1 karena lembar jawaban bagian S-1A tidak memiliki kriteria skor 0 pada dataset training.
    "S-1A": [1, 2, 3, 4],
    "S-1B": [0, 1, 2, 3, 4],
    "S-1C": [0, 1, 2, 3, 4],
    "S-1D": [0, 1, 2, 3, 4],
    "S-1E": [0, 1, 2, 3, 4],
    "S-1F": [0, 1, 2, 3, 4, 5],

    "S-2A": [0, 1, 2, 3, 4],
    # S-2B: Skor melompat dari 2 ke 4 karena tidak terdapat sampel data latih dengan skor 3 pada dataset asli (label encoding artifact).
    "S-2B": [0, 1, 2, 4],
    "S-2C": [0, 1, 2, 3, 4],
    "S-2D": [0, 1, 2, 3, 4],
    "S-2E": [0, 1, 2, 3, 4],
    "S-2F": [0, 1, 2, 3, 4, 5],

    "S-3A": [0, 1, 2, 3, 4],
    "S-3B": [0, 1, 2, 3, 4],
    "S-3C": [0, 1, 2, 3, 4],
    "S-3D": [0, 1, 2, 3, 4],
    "S-3E": [0, 1, 2, 3, 4],
    # S-3F: Skor melompat dari 3 ke 5 karena tidak terdapat sampel data latih dengan skor 4 pada dataset asli (label encoding artifact).
    "S-3F": [0, 1, 2, 3, 5],

    "S-4A": [0, 1, 2, 3, 4],
    "S-4B": [0, 1, 2, 3, 4],
    "S-4C": [0, 1, 2, 3, 4],
    "S-4D": [0, 1, 2, 3, 4],
    "S-4E": [0, 1, 2, 3, 4],
    "S-4F": [0, 1, 2, 3, 4, 5],
}


def get_score(section_code: str, predicted_class: int) -> int:
    """
    Convert predicted_class → score berdasarkan CLASS_SCORE_MAP.

    Parameter:
        section_code    : kode section, contoh "S-1A"
        predicted_class : integer index kelas dari argmax(softmax)

    Return:
        score (int) — 0 jika mapping belum diisi atau class tidak ditemukan
    """
    mapping = CLASS_SCORE_MAP.get(section_code, [])
    if 0 <= predicted_class < len(mapping):
        return mapping[predicted_class]
    return 0
