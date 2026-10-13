# Atom Rearrangement Workbench — English Edition

[![Version](https://img.shields.io/badge/version-1.0.0-0072BD)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A local interactive application for teaching, demonstrations, and exploratory comparisons of single-species atom rearrangement. It runs algorithms and physical error models from [bernienlab/atommovr](https://github.com/bernienlab/atommovr).

This repository is the English edition of the shared workbench implementation. The [Chinese edition](https://github.com/aa3277105147-create/atommovr-ui-zh) is maintained separately.

## Features

- Six upstream algorithms: Parallel Hungarian, Hungarian, Parallel LBAP, Generalized Balance, BCv2, and Balance & Compact.
- Central-square, checkerboard, horizontal-stripe, and vertical-stripe targets; random loading or manual initial occupancy.
- An active-tweezer limit of 1–24 for supported parallel algorithms, including every crossed-AOD intersection. Sequential Hungarian and the conservative LBAP execution mode use one tweezer.
- Tweezer speed, lattice spacing, atom lifetime, pickup and putdown success rates, and operation durations.
- Play, pause, replay, step, seek, and presentation speeds from 0.25× to 4×.
- Comparisons using a shared initial state, repeated trials, complete trajectory JSON, and per-trial CSV exports.

## Quick start

Install [Python 3.11 or later](https://www.python.org/downloads/) and [Git](https://git-scm.com/), then download or clone this repository. Run the launcher from the repository directory:

| Platform | Launcher |
|---|---|
| Windows | Double-click **start.bat**, or run `.\start.bat` in PowerShell |
| Linux | Run `chmod +x start.sh && ./start.sh` |
| macOS | Double-click **Launch.command**, or run `./start.sh` |

The entry points use the same [launch.py](launch.py) setup logic. The first launch prepares a Python environment and obtains the upstream dependency if needed. Network access is required for this setup. Parallel LBAP may need a local C compiler on its first run to build the platform-specific PPSU matching library.

The browser opens a local address, usually <http://127.0.0.1:7860>. Keep the terminal open while using the app; press **Control-C** to stop it. For platform-specific validation coverage, see [VALIDATION.md](VALIDATION.md).

### Existing upstream source

An existing installation can be selected with the **ATOMMOVR_SOURCE** environment variable. It must point to the complete upstream source directory, including **PPSU2023**, rather than just the Python package.

Set **ATOMMOVR_PYTHON** to a Python 3.11+ executable when a specific interpreter is required. A virtual-environment interpreter is used directly; a base interpreter creates or reuses this repository's `.venv`.

Managed downloads use upstream revision **cca2553985bb9d81b19cae9b83074df4816502f9**. A source directory supplied by the user may have a different revision; keep track of that revision when reproducing results.

## Manual installation

The complete upstream source is required because LBAP uses the top-level PPSU2023 component. From this repository, on Linux or macOS:

~~~bash
git clone https://github.com/bernienlab/atommovr.git
git -C atommovr checkout cca2553985bb9d81b19cae9b83074df4816502f9
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e ./atommovr
ATOMMOVR_SOURCE="$PWD/atommovr" .venv/bin/python app.py
~~~

Use a Python 3.11+ interpreter for the environment. On Windows PowerShell:

~~~powershell
git clone https://github.com/bernienlab/atommovr.git
git -C atommovr checkout cca2553985bb9d81b19cae9b83074df4816502f9
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .\atommovr
$env:ATOMMOVR_SOURCE = (Resolve-Path .\atommovr).Path
.venv\Scripts\python.exe app.py
~~~

## Using the workbench

Changing parameters updates the initial-state and target preview. Select **Run simulation** to compute a new trajectory. Replay and presentation speed reuse the stored result.

The tweezer limit applies to all active AOD intersections, including empty and stationary intersections. It is a capacity limit, not a promise that every batch uses that many tweezers.

- [User guide](USER_GUIDE.md)
- [Algorithms and comparison methodology](ALGORITHMS.md)
- [Feature scope and extension priorities](FEATURE_SCOPE.md)
- [Validation records](VALIDATION.md)

## Validation

The shared implementation passed 62 Python behavior tests before the initial release. Test scope, platform coverage, measured results, and English-edition release checks are documented in [VALIDATION.md](VALIDATION.md).

With dependencies installed, run the Python checks from the repository:

~~~bash
python -m unittest discover -s . -p 'test_*.py' -v
~~~

Use the Python interpreter from the environment used to run the app. Node.js can check the player syntax with `node --check player.js`; it is not required to use the workbench.

## Project contributions and upstream attribution

This project independently implements the interaction layer, Canvas player, initial-state editing and preview, result-recording adapters, capacity and point-trajectory safety scheduling, comparison tools, exports, and launch utilities. These are the workbench's contributions; they are not a claim to have invented the underlying rearrangement algorithms or a new physical simulation engine.

The six rearrangement algorithms, atom-array operations, loading and error models, AOD semantics, and physical timing rules come from **atommovr**, by Nikhil K. Harle, Bo-Yu Chen, Bob Bao, and Hannes Bernien. This workbench is maintained independently and is not an official or endorsed upstream release. The repository does not vendor upstream source; setup downloads or reads a separate copy.

For research using the upstream framework, cite:

> N. K. Harle, B.-Y. Chen, B. Bao, and H. Bernien, “atommovr: An open-source simulation framework for rearrangement in atomic arrays,” *Quantum* **10**, 2177 (2026). [DOI: 10.22331/q-2026-07-29-2177](https://doi.org/10.22331/q-2026-07-29-2177)

The workbench's new code is released under the [MIT License](LICENSE), with copyright attributed to **aa3277105147-create**. Upstream and other dependencies retain their own copyright and license notices; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Model boundaries

Safety checks use lattice sites, synchronous straight paths, and point-like traps. They do not validate complete hardware waveforms, finite beam sizes, beat frequencies, optical power, or heating. Added acceleration and deceleration durations are fixed timing overheads, not simulated velocity profiles. Single cases and small repeated-trial samples describe the selected conditions and do not establish a universal algorithm ranking.
