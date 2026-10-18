"""Select a usable, administrator-provisioned Python for this CI job only."""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

from bootstrap_sources import project_inputs

PROVISIONED_ROOT = Path("/opt/python")
PROBE = (
    "import ctypes,json,sqlite3,ssl,sys,venv;"
    "print(json.dumps({'version':list(sys.version_info[:3]),"
    "'implementation':sys.implementation.name}))"
)


def trusted_path(path):
    """Reject links and paths writable by anyone except the administrator."""
    try:
        metadata = [part.lstat() for part in (path, *path.parents)]
    except OSError:
        return False
    return all(
        item.st_uid == 0 and not item.st_mode & 0o022 and not stat.S_ISLNK(item.st_mode)
        for item in metadata
    )


def usable(path, version):
    if not path.is_file() or not trusted_path(path):
        return False
    try:
        result = subprocess.run(
            [str(path), "-I", "-B", "-c", PROBE],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0 and json.loads(result.stdout) == {
            "version": list(version),
            "implementation": "cpython",
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False


def select_python(floor):
    if not trusted_path(PROVISIONED_ROOT):
        raise ValueError("Trusted provisioned Python directory is unavailable")
    pattern = re.compile(re.escape(floor) + r"\.(0|[1-9][0-9]*)")
    candidates = sorted(
        (
            (tuple(map(int, directory.name.split("."))), directory)
            for directory in PROVISIONED_ROOT.iterdir()
            if pattern.fullmatch(directory.name)
        ),
        reverse=True,
    )
    for version, directory in candidates:
        python = directory / "bin" / ("python" + floor)
        if usable(python, version):
            return python
    raise ValueError(
        f"No usable administrator-provisioned CPython {floor} in {PROVISIONED_ROOT}; "
        "CI requires an existing compatible interpreter; downloads are disabled"
    )


def main():
    root = Path(__file__).resolve().parents[1]
    _, _, floor = project_inputs(root)
    python = select_python(floor)
    with Path(os.environ["GITHUB_PATH"]).open("a") as output:
        output.write(str(python.parent) + "\n")
    with Path(os.environ["GITHUB_ENV"]).open("a") as output:
        output.write("CONNECTOR_BOOTSTRAP_PYTHON=" + str(python) + "\n")
    print(json.dumps({"python": str(python), "declared_minimum": floor}))


if __name__ == "__main__":
    main()
