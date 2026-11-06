"""Early packaging test: build the smoke program with PyInstaller and run it.

See ``specs/packaging.md``. Usage: ``.venv\\Scripts\\python.exe tools\\check_packaging.py
[--no-build]``. Builds ``packaging/smoke.spec`` into ``build/packaging/dist``, runs the executable
(windowed: its answers are files in ``build/packaging/out``), and checks what a packaged MiTerm-N5
needs: the window, a program under ConPTY, a new session, pywinpty's files, pyte as separate files,
the log written without console.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BUILD = ROOT / "build" / "packaging"
DIST = BUILD / "dist"
OUT = BUILD / "out"
NAME = "n5terminal-smoke"
FOLDER = DIST / NAME
TIMEOUT = 180


def build() -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD / "work"),
        str(ROOT / "packaging" / "smoke.spec"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def run_executable() -> int:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    completed = subprocess.run(
        [str(FOLDER / f"{NAME}.exe"), "--out", str(OUT)], timeout=TIMEOUT, check=False
    )
    return completed.returncode


def folder_size() -> float:
    return sum(path.stat().st_size for path in FOLDER.rglob("*") if path.is_file()) / 1024 / 1024


def report(name: str) -> dict[str, object] | None:
    path = OUT / f"{name}.json"
    if not path.exists():
        return None
    data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true", help="run the last build again")
    args = parser.parse_args()
    if not args.no_build:
        build()
    code = run_executable()
    print(f"exit code of the executable: {code}")
    print(f"folder: {FOLDER} ({folder_size():.0f} MB)")
    problems: list[str] = []
    if code != 0:
        problems.append(f"the executable ended with code {code}")
    for role in ("parent", "child"):
        data = report(role)
        if data is None:
            problems.append(f"no report from the {role} session")
            continue
        print(f"--- {role}\n{json.dumps(data, indent=2)}")
        if not data.get("ok"):
            problems.append(f"the {role} session reports a failure")
        if data.get("frozen") is not True:
            problems.append(f"the {role} session does not run frozen")
        if data.get("stdout_is_none") is not True:
            problems.append(f"the {role} session has a console")
        if not (OUT / f"{role}.log").exists() or not (OUT / f"{role}.log").stat().st_size:
            problems.append(f"no log written by the {role} session")
    for problem in problems:
        print(f"PROBLEM: {problem}")
    print("packaging test:", "FAILED" if problems else "passed")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
