"""Shared local setup and launcher for Windows, Linux, and macOS."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
UPSTREAM_URL = "https://github.com/bernienlab/atommovr.git"
UPSTREAM_REF = "cca2553985bb9d81b19cae9b83074df4816502f9"
MIN_PYTHON = (3, 11)


class SetupError(RuntimeError):
    pass


def run(command, *, cwd=None, env=None, capture=False):
    return subprocess.run(
        [str(part) for part in command], cwd=cwd, env=env, check=True,
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def complete_source(path):
    return ((path / "atommovr" / "__init__.py").is_file()
            and (path / "pyproject.toml").is_file()
            and (path / "PPSU2023" / "setupc.py").is_file())


def find_source(*, check_only=False):
    override = os.environ.get("ATOMMOVR_SOURCE")
    if override:
        source = Path(override).expanduser().resolve()
        if not complete_source(source):
            raise SetupError(f"ATOMMOVR_SOURCE is not a complete atommovr source directory: {source}")
        return source
    downloaded = Path.home() / "Downloads" / "atommovr-main"
    cached = HERE / ".deps" / "atommovr"
    for candidate in (downloaded, cached):
        if complete_source(candidate):
            return candidate.resolve()
    if check_only:
        raise SetupError("No source checkout was found. A normal launch will download the pinned revision, or set ATOMMOVR_SOURCE first.")
    if cached.exists():
        raise SetupError(f"The cached source is incomplete. Repair or move it, then retry: {cached}")
    if not shutil.which("git"):
        raise SetupError("Git is required for the automatic source download. Install Git or set ATOMMOVR_SOURCE.")
    print("Downloading the pinned atommovr source revision…", flush=True)
    cached.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".atommovr-install-", dir=cached.parent) as temporary:
        checkout = Path(temporary) / "checkout"
        run(["git", "clone", "--no-checkout", UPSTREAM_URL, checkout])
        run(["git", "-C", checkout, "checkout", "--detach", UPSTREAM_REF])
        actual = run(["git", "-C", checkout, "rev-parse", "HEAD"], capture=True).stdout.strip()
        if actual != UPSTREAM_REF or not complete_source(checkout):
            raise SetupError("The downloaded revision or source directory is incomplete. Check the network connection and retry.")
        checkout.rename(cached)
    return cached.resolve()


def venv_python(directory, *, windows=None):
    if windows is None:
        windows = os.name == "nt"
    return directory / ("Scripts/python.exe" if windows else "bin/python")


def python_info(executable):
    try:
        completed = run([executable, "-c", "import json,sys; print(json.dumps({'version':list(sys.version_info[:3]),'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"], capture=True)
        info = json.loads(completed.stdout)
        return info if tuple(info["version"][:2]) >= MIN_PYTHON else None
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        return None


def find_python(source, *, check_only=False):
    base_python = sys.executable
    override = os.environ.get("ATOMMOVR_PYTHON")
    if override:
        chosen = Path(shutil.which(override) or override).expanduser().absolute()
        info = python_info(chosen)
        if not info:
            raise SetupError("ATOMMOVR_PYTHON must point to a working Python 3.11+ interpreter executable.")
        if info["prefix"] != info["base_prefix"]:
            return chosen
        base_python = str(chosen)
    # An explicit base Python prepares/reuses the UI's .venv. An explicit
    # virtual-env Python is used directly, without touching a global install.
    candidates = (HERE / ".venv",) if override else (HERE / ".venv", source / ".venv")
    for directory in candidates:
        executable = venv_python(directory)
        if executable.is_file() and python_info(executable):
            # Resolving a Unix venv symlink would select the global interpreter
            # and install packages outside the virtual environment.
            return executable.absolute()
    if check_only:
        raise SetupError("No Python 3.11+ virtual environment is ready. A normal launch will create the local .venv.")
    if not override and sys.version_info[:2] < MIN_PYTHON:
        raise SetupError("Python 3.11 or newer is required.")
    directory = HERE / ".venv"
    if directory.exists():
        raise SetupError(f"The existing virtual environment is unusable. Repair or move this directory first: {directory}")
    print("Creating the local Python virtual environment…", flush=True)
    run([base_python, "-m", "venv", directory])
    executable = venv_python(directory)
    if not executable.is_file() or not python_info(executable):
        raise SetupError("Virtual-environment creation failed. Confirm that Python includes venv and ensurepip.")
    return executable.absolute()


def requirements():
    files, seen = [], set()
    def visit(path):
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        data = path.read_bytes()
        files.append((str(path.relative_to(HERE)), data.decode("utf-8")))
        for line in data.decode("utf-8").splitlines():
            line = line.strip()
            if line.startswith("-r "):
                visit(path.parent / line[3:].strip())
    visit(HERE / "requirements.txt")
    return files


def dependency_fingerprint(source, executable):
    payload = {"schema": 1, "python": str(executable), "runtime": python_info(executable),
               "source": str(source), "upstream_pyproject": (source / "pyproject.toml").read_text(encoding="utf-8"),
               "requirements": requirements()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def dependencies_ready(executable, source):
    probe = """
import importlib.metadata as metadata
import sys, tomllib
from packaging.requirements import Requirement
with open(sys.argv[1], 'rb') as stream:
    required = tomllib.load(stream)['project'].get('dependencies', [])
def add_file(path):
    from pathlib import Path
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('-r '):
            add_file(Path(path).parent / line[3:].strip())
        else:
            required.append(line)
add_file(sys.argv[2])
for text in required:
    requirement = Requirement(text)
    if requirement.marker is None or requirement.marker.evaluate():
        version = metadata.version(requirement.name)
        if requirement.specifier and version not in requirement.specifier:
            raise RuntimeError(f'{requirement.name}: incompatible version {version}')
import gradio, numpy, scipy, xarray, matplotlib
from atommovr.algorithms.single_species import ParallelHungarian, ParallelLBAP
"""
    try:
        run([executable, "-c", probe, source / "pyproject.toml", HERE / "requirements.txt"],
            cwd=source, capture=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def install_dependencies(executable, source, *, reinstall=False):
    marker = HERE / ".runtime" / "dependencies.json"
    fingerprint = dependency_fingerprint(source, executable)
    try:
        previous = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if not reinstall and previous.get("fingerprint") == fingerprint and dependencies_ready(executable, source):
        return
    print("Preparing the interface and upstream dependencies. The first run may take several minutes…", flush=True)
    run([executable, "-m", "pip", "install", "-r", HERE / "requirements.txt"])
    run([executable, "-m", "pip", "install", "-e", source])
    if not dependencies_ready(executable, source):
        raise SetupError("Dependency checks still fail after installation. Review the installation output or retry with --reinstall.")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"fingerprint": fingerprint}, indent=2), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prepare the local environment and launch the atommovr interface. Application arguments such as --no-browser are forwarded.",
        epilog="ATOMMOVR_SOURCE selects a complete source checkout. ATOMMOVR_PYTHON selects an interpreter: a virtual-environment interpreter is used directly, while a base interpreter creates or reuses this directory's .venv. start.bat handles Windows py -3.11/py -3 discovery.",
    )
    parser.add_argument("--check", action="store_true", help="check the existing environment without downloading, installing, or starting the service")
    parser.add_argument("--reinstall", action="store_true", help="check and install dependencies again")
    options, application_args = parser.parse_known_args(argv)
    try:
        source = find_source(check_only=options.check)
        executable = find_python(source, check_only=options.check)
        if options.check:
            if not dependencies_ready(executable, source):
                raise SetupError("Dependencies are not ready. Launch without --check to complete installation.")
            print(f"Environment check passed.\nSource: {source}\nPython: {executable}", flush=True)
            return 0
        install_dependencies(executable, source, reinstall=options.reinstall)
        environment = os.environ.copy()
        environment["ATOMMOVR_SOURCE"] = str(source)
        environment.setdefault("ATOMMOVR_UI_STATE_DIR", str(HERE / ".runtime"))
        environment["GRADIO_ANALYTICS_ENABLED"] = "False"
        environment["MPLBACKEND"] = "Agg"
        # Prepare the optional C library outside the simulator time budget.
        native = subprocess.run(
            [str(executable), "-c", "from atommovr.algorithms.source.PPSU_weight_matching import _get_lib; _get_lib()"],
            cwd=source, env=environment, check=False,
        )
        if native.returncode:
            print("The native LBAP component could not be prepared; a C compiler may be required. Other algorithms can still start, and LBAP will report an error if selected.", flush=True)
        return subprocess.call([str(executable), str(HERE / "app.py"), *application_args],
                               cwd=HERE, env=environment)
    except KeyboardInterrupt:
        return 130
    except (SetupError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Launch failed: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
