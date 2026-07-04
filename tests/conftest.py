import os
from pathlib import Path


TEST_ENVIRONMENT = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SECRET_KEY": "test-secret-key-placeholder-only",
    "REDIS_URL": "redis://127.0.0.1:6379/0",
    "MODEL_ROOT": str((Path.cwd() / "Models").resolve()),
    "ALLOWED_ORIGINS": "http://localhost:3000",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "WARNING",
    "RQ_JOB_TIMEOUT": "1800",
}

for name, value in TEST_ENVIRONMENT.items():
    os.environ.setdefault(name, value)
