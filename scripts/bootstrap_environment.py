#!/usr/bin/env python3
"""Prepare a locked, source-contract environment without building dependencies."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from bootstrap_sources import checkout_source, project_inputs, run, sha256


def sync_commands(uv, python, bindings, *, root):
    common = [
        "--no-build",
        "--no-python-downloads",
        "--python",
        python,
        "--project",
        str(root),
        "--directory",
        str(root),
    ]
    exclusions = [
        argument
        for source in bindings
        for argument in ("--no-install-package", source["name"])
    ]
    return [
        [uv, "lock", "--check", *common],
        [
            uv,
            "sync",
            "--frozen",
            "--extra",
            "test",
            "--no-install-project",
            *exclusions,
            *common,
        ],
    ]


def add_source_paths(root, python, sources, *, env):
    purelib = Path(
        run(
            [
                str(python),
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
            ],
            root=root,
            env=env,
        )
    )
    purelib.resolve().relative_to((root / ".ci" / "connector-venv").resolve())
    paths = [root, *sources]
    if any("\n" in str(path) or "\r" in str(path) for path in paths):
        raise ValueError("Source paths must not contain line breaks")
    target = purelib / "_connector_sources.pth"
    if target.is_symlink():
        raise ValueError("Source path configuration must not be a symlink")
    target.write_text("\n".join(map(str, paths)) + "\n")


def inspect_environment(root, python, *, bindings, sources, env):
    expected = {
        binding["module"]: str(source)
        for binding, source in zip(bindings, sources, strict=True)
    }
    project_names = tomllib.loads((root / "pyproject.toml").read_text())["tool"][
        "pipelines_hooks"
    ]["packages"]
    expected.update({module: str(root) for module in project_names})
    probe = """
import importlib, importlib.metadata, json, pathlib, sys
expected = json.loads(sys.argv[1])
prefix = pathlib.Path(sys.prefix).resolve()
if prefix != pathlib.Path(sys.argv[2]).resolve():
    raise ValueError('Unexpected interpreter environment')
origins = {}
for name, source in expected.items():
    module = importlib.import_module(name)
    origin = pathlib.Path(module.__file__).resolve()
    origin.relative_to(pathlib.Path(source).resolve())
    origins[name] = str(origin)
for name in ('agent_connector_sdk', 'epistemic_graph', 'fastmcp', 'mcp', 'pytest'):
    origin = pathlib.Path(importlib.import_module(name).__file__).resolve()
    origin.relative_to(pathlib.Path(expected.get(name, prefix)).resolve())
    origins[name] = str(origin)
distributions = sorted((item.metadata['Name'], item.version) for item in importlib.metadata.distributions())
print(json.dumps({'executable': sys.executable, 'python': sys.version, 'source_imports': origins, 'installed_distributions': distributions}))
"""
    return json.loads(
        run(
            [
                str(python),
                "-c",
                probe,
                json.dumps(expected),
                str(root / ".ci/connector-venv"),
            ],
            root=root,
            env=env,
        )
    )


def export_github(python):
    if any(character in str(python) for character in "\r\n"):
        raise ValueError("Interpreter paths must not contain line breaks")
    with Path(os.environ["GITHUB_PATH"]).open("a") as output:
        output.write(str(python.parent) + "\n")
    with Path(os.environ["GITHUB_ENV"]).open("a") as output:
        output.write("GENERATED_SCHEMA_PYTHON=" + str(python) + "\n")
        output.write("VIRTUAL_ENV=" + str(python.parent.parent) + "\n")
        output.write("PYTHONPATH=\nPYTHONHOME=\nPYTHONNOUSERSITE=1\n")
        output.write("PYTHONDONTWRITEBYTECODE=1\nMCP_FLEET_REGISTRATION=false\n")


def workspace_environment(root):
    ci = root / ".ci"
    if ci.is_symlink():
        raise ValueError("The CI workspace must not be a symlink")
    ci.mkdir(exist_ok=True)
    for relative in ("sources", "connector-venv"):
        if (ci / relative).is_symlink():
            raise ValueError("The bootstrap directories must not be symlinks")
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "UV_PROJECT",
        "UV_WORKING_DIR",
        "UV_WORKING_DIRECTORY",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
    ):
        env.pop(key, None)
    env.update(
        UV_PROJECT_ENVIRONMENT=str(ci / "connector-venv"),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        MCP_FLEET_REGISTRATION="false",
    )
    return ci, env


def validated_interpreter(floor):
    """Bind uv to this process, never a rediscovered minor-version request."""
    if sys.implementation.name != "cpython" or sys.version_info[:2] != tuple(
        map(int, floor.split("."))
    ):
        raise ValueError(f"Run bootstrap with the declared CPython {floor} minimum")
    python = Path(sys.executable)
    if not python.is_absolute():
        raise ValueError("Bootstrap interpreter must have an absolute path")
    selected = os.environ.get("CONNECTOR_BOOTSTRAP_PYTHON", str(python))
    if selected != str(python):
        raise ValueError("Bootstrap interpreter differs from the selected executable")
    return str(python)


def prepare(root, *, uv="uv", github=False):
    root = root.resolve()
    project, bindings, floor = project_inputs(root)
    selected_python = validated_interpreter(floor)
    ci, env = workspace_environment(root)
    original_lock = sha256(root / "uv.lock")
    original_project = sha256(root / "pyproject.toml")
    sources = [checkout_source(root, binding, env) for binding in bindings]
    commands = sync_commands(uv, selected_python, bindings, root=root)
    for command in commands:
        subprocess.run(command, cwd=root, env=env, check=True)
    if (sha256(root / "uv.lock"), sha256(root / "pyproject.toml")) != (
        original_lock,
        original_project,
    ):
        raise ValueError("Bootstrap must not rewrite reviewed dependency inputs")
    python = (
        ci
        / "connector-venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    add_source_paths(root, python, sources, env=env)
    environment = inspect_environment(
        root, python, bindings=bindings, sources=sources, env=env
    )
    record = {
        "scope": "Locked wheel dependencies with explicit project, SDK and EG source imports",
        "complete_wheel_installation_certified": False,
        "native_builds": False,
        "project": project["project"]["name"],
        "bootstrap_python": selected_python,
        "pyproject_sha256": original_project,
        "lock_sha256": original_lock,
        "uv_version": run([uv, "--version"], root=root, env=env),
        "sources": bindings,
        "commands": commands,
        "environment": environment,
    }
    write_receipt(ci, record)
    if github:
        export_github(python)
    return record


def write_receipt(ci, record):
    target = ci / "connector-environment.json"
    if target.is_symlink():
        raise ValueError("Environment receipt must not be a symlink")
    target.write_text(json.dumps(record, indent=2) + "\n")
    target.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--uv", default="uv")
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, uv=args.uv, github=args.github), indent=2))


if __name__ == "__main__":
    main()
