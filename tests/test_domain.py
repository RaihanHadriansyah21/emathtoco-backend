from domain import (
    MAX_SCORE_BY_SECTION,
    MAX_TOTAL_SCORE,
    SECTION_CODES,
    get_domain_contract,
)


def test_section_contract_is_complete() -> None:
    assert len(SECTION_CODES) == 24
    assert len(set(SECTION_CODES)) == 24
    assert SECTION_CODES[0] == "S-1A"
    assert SECTION_CODES[-1] == "S-4F"


def test_score_contract_totals_one_hundred() -> None:
    assert sum(MAX_SCORE_BY_SECTION.values()) == MAX_TOTAL_SCORE


def test_serialized_domain_contract_matches_runtime_enums() -> None:
    contract = get_domain_contract()
    assert contract["ai_models"] == [
        "MobileNetV2",
        "DenseNet121",
        "InceptionV3",
    ]
    assert contract["user_roles"] == ["admin", "dosen", "mahasiswa"]
    assert contract["section_codes"] == list(SECTION_CODES)
