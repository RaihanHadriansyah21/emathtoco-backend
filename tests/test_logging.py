from utils.logging_helper import redact


def test_logger_redacts_tokens_and_email() -> None:
    message = (
        "Bearer eyJabc.def.ghi "
        "sb_secret_abcdefghijklmnopqrstuvwxyz "
        "student@example.com"
    )
    redacted = redact(message)
    assert "eyJabc" not in redacted
    assert "sb_secret_" not in redacted
    assert "student@example.com" not in redacted
