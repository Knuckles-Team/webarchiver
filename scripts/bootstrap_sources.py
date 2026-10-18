"""Bind bootstrap inputs and immutable source checkouts before dependency sync."""

import hashlib
import re
import subprocess
import tomllib
from urllib.parse import urlsplit

SOURCE_MODULES = {
    "agent-connector-sdk": "agent_connector_sdk",
    "epistemic-graph": "epistemic_graph",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, *, root, env):
    return subprocess.check_output(command, cwd=root, env=env, text=True).strip()


def source_coordinates(name, source):
    """Validate the immutable, credential-free source declaration."""
    if set(source) != {"git", "rev"}:
        raise ValueError(f"{name} requires one immutable Git source")
    url, revision = source["git"], source["rev"]
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[0-9a-f]{40}", revision)
    ):
        raise ValueError(f"{name} requires credential-free HTTPS and a full commit ID")
    return url, revision


def locked_source_package(name, lock, url, revision):
    """Require one lock entry with the exact declared Git source."""
    packages = [row for row in lock["package"] if row["name"] == name]
    expected = {"git": f"{url}?rev={revision}#{revision}"}
    if len(packages) != 1 or packages[0]["source"] != expected:
        raise ValueError(f"{name} source differs between pyproject.toml and uv.lock")
    return packages[0]


def source_binding(name, project, lock):
    url, revision = source_coordinates(name, project["tool"]["uv"]["sources"][name])
    package = locked_source_package(name, lock, url, revision)
    return {
        "name": name,
        "module": SOURCE_MODULES[name],
        "url": url,
        "revision": revision,
        "version": package["version"],
    }


def project_inputs(root):
    project = tomllib.loads((root / "pyproject.toml").read_text())
    lock = tomllib.loads((root / "uv.lock").read_text())
    if "test" not in project["project"].get("optional-dependencies", {}):
        raise ValueError("Declare the test extra before preparing the test environment")
    match = re.search(r">=\s*(3\.\d+)", project["project"]["requires-python"])
    if match is None:
        raise ValueError("The project must declare its Python minor-version floor")
    configured = project.get("tool", {}).get("uv", {}).get("sources", {})
    sources = [
        source_binding(name, project, lock)
        for name in SOURCE_MODULES
        if name in configured
    ]
    return project, sources, match.group(1)


def checkout_source(root, binding, env):
    target = root / ".ci" / "sources" / (binding["name"] + "-" + binding["revision"])
    if target.is_symlink() or (target / ".git").is_symlink():
        raise ValueError("Source checkout must not contain redirected Git directories")
    if not target.exists():
        fetch_source(root, target, binding=binding, env=env)
    if target.is_symlink() or not (target / ".git").is_dir():
        raise ValueError("Source checkout must be an ordinary Git directory")
    head = run(["git", "-C", str(target), "rev-parse", "HEAD"], root=root, env=env)
    dirty = run(
        ["git", "-C", str(target), "status", "--porcelain", "--ignored"],
        root=root,
        env=env,
    )
    if (
        head != binding["revision"]
        or dirty
        or not (target / binding["module"]).is_dir()
    ):
        raise ValueError(f"{binding['name']} checkout is stale, dirty or incomplete")
    return target


def fetch_source(root, target, *, binding, env):
    target.mkdir(parents=True)
    run(["git", "init", "--quiet", str(target)], root=root, env=env)
    run(
        ["git", "-C", str(target), "remote", "add", "origin", binding["url"]],
        root=root,
        env=env,
    )
    run(
        [
            "git",
            "-C",
            str(target),
            "fetch",
            "--depth=1",
            "--filter=blob:none",
            "origin",
            binding["revision"],
        ],
        root=root,
        env=env,
    )
    run(
        ["git", "-C", str(target), "checkout", "--detach", binding["revision"]],
        root=root,
        env=env,
    )
