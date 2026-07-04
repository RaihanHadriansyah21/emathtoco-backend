"""Safe local entrypoint for the database security proof suite.

This file intentionally contains no credentials, user fixtures, or cloud
mutation logic. The authoritative tests live under supabase/tests/.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    npx = shutil.which("npx")
    if not npx:
        print("npx is required to run the local Supabase proof suite.")
        return 2

    commands = (
        [npx, "supabase", "db", "reset", "--local"],
        [npx, "supabase", "db", "test"],
        [npx, "supabase", "db", "lint", "--local", "--level", "warning"],
    )
    for command in commands:
        completed = subprocess.run(command, cwd=project_root, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
