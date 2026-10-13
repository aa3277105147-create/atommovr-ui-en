"""Compare original atommovr algorithms from one frozen initial array."""

from __future__ import annotations

import copy
import math
import time
from typing import Any

import simulator


TABLE_HEADERS = [
    "Algorithm", "Status", "Target fill", "Tweezer limit", "Peak active", "Transport batches", "Successful transports",
    "Successful distance (µm)", "Simulated time (µs)",
]

_LABELS = {
    "parallel": "Parallel Hungarian",
    "hungarian": "Hungarian (sequential transport)",
    "bcv2": "Balance & Compact (BCv2)",
    "bc": "Balance & Compact (BC)",
    "lbap": "Parallel LBAP",
    "parallel_lbap": "Parallel LBAP",
    "generalized": "Generalized Balance",
}
_STATUS_TEXT = {
    "success": "Target filled", "incomplete": "Incomplete",
    "insufficient": "Insufficient atoms", "algorithm_error": "Execution failed",
    "invalid": "Invalid parameters", "skipped": "Unsupported pattern", "blocked": "Collision safety stop", "not_run": "Not run",
}


def _algorithm_label(key: str, implementation: Any) -> str:
    labels = getattr(simulator, "ALGORITHM_NAMES", getattr(simulator, "ALGORITHM_LABELS", {}))
    return labels.get(key, _LABELS.get(key, getattr(implementation, "__name__", key)))


def _supports_pattern(key: str, pattern: str) -> bool:
    supported = getattr(simulator, "SUPPORTED_PATTERNS_BY_ALGORITHM", getattr(simulator, "ALGORITHM_PATTERNS", {}))
    if key in supported:
        return pattern in supported[key]
    return pattern == "center" if key in ("bc", "bcv2") else True


def _successful_transports(result: dict[str, Any], spacing_um: float) -> tuple[int, float]:
    """Count successful nonzero-distance commands originating at occupied sites.

    AOD completion may record empty-site commands and failed pickups. They are
    deliberately excluded, as are transport/putdown losses whose actual
    traveled distances are not available in the library's event records.
    """
    count = 0
    distance = 0.0
    for frame in result.get("frames", []):
        before = frame.get("before", [])
        for move in frame.get("moves", []):
            if move.get("event") != 0 or move.get("flag") != 0:
                continue
            source, destination = move.get("from"), move.get("to")
            if not isinstance(source, (tuple, list)) or not isinstance(destination, (tuple, list)):
                continue
            if len(source) != 2 or len(destination) != 2:
                continue
            r, c = source
            if not (isinstance(r, int) and isinstance(c, int) and
                    0 <= r < len(before) and 0 <= c < len(before[r]) and before[r][c]):
                continue
            length = math.hypot(destination[0] - r, destination[1] - c)
            if length <= 0:
                continue
            count += 1
            distance += length * spacing_um
    return count, distance


def _footnote(noise: bool) -> str:
    text = (
        "Algorithms share the same initial distribution, target, and physical parameters; atoms outside the target are retained. Results include this interface's capacity limits and collision-aware scheduling. "
        "Algorithms with multiple-tweezer support use the selected limit; conservative sequential options use one tweezer. Counts include empty AOD intersections. "
        "Successful transports count successful, nonzero-distance moves from occupied sites, excluding empty-site commands and failures. Multiple moves of the same atom are counted separately. "
        "Distance sums only these successful paths. Simulated physical time follows batch timing and consecutive-move rules, independently of playback speed. "
    )
    if noise:
        text += (
            "Error mode compares a single trial using the same error seed. "
            "Algorithms have different execution orders and consume different random samples; one seed does not establish a statistical success rate. "
            "A shorter distance can also result from failed transports, so interpret it alongside target fill."
        )
    return text


def _row(key: str, label: str, summary: dict[str, Any], successful_moves: int | None,
         successful_distance_um: float | None, target_count: int,
         tweezer_count: int | None = None) -> dict[str, Any]:
    status = summary.get("status", "algorithm_error")
    filled = summary.get("filled")
    total = summary.get("target_count", target_count)
    fill_fraction = filled / total if filled is not None and total else None
    fill_text = "—" if filled is None else f"{filled}/{total}"
    if fill_fraction is not None:
        fill_text += f" ({fill_fraction * 100:.1f}%)"
    elapsed = summary.get("simulated_time")
    return {
        "algorithm": label, "key": key, "status": status,
        "status_text": _STATUS_TEXT.get(status, status), "filled": filled,
        "target_count": total, "fill_fraction": fill_fraction, "fill_text": fill_text,
        "tweezer_count": summary.get("tweezer_count", tweezer_count),
        "max_active_tweezers": summary.get("max_active_tweezers"),
        "executed_batches": summary.get("executed_batches"),
        "successful_moves": successful_moves,
        "successful_distance_um": successful_distance_um,
        "simulated_time_us": None if elapsed is None else elapsed * 1_000_000,
        "message": summary.get("message", ""),
        "losses": summary.get("losses"),
    }


def _table_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    def number(value: int | float | None) -> int | float | str:
        return "—" if value is None else round(value, 6)
    return [[
        row["algorithm"], row["status_text"], row["fill_text"],
        number(row["tweezer_count"]), number(row["max_active_tweezers"]),
        number(row["executed_batches"]), number(row["successful_moves"]),
        number(row["successful_distance_um"]), number(row["simulated_time_us"]),
    ] for row in rows]


def compare_algorithms(config: dict[str, Any] | None = None, *, deadline=None, on_progress=None) -> dict[str, Any]:
    """Run every available native algorithm with one identical frozen matrix.

    The returned config remains the normalized *original* user configuration.
    Per-algorithm copies use manual initial arrays solely to freeze the same
    random/manual preview. simulate() preserves native error seeds and already
    applies process time/resource limits and do_ejection=False.
    """
    base = simulator.preview(copy.deepcopy(config))
    normalized = copy.deepcopy(base.get("config", {}))
    footnote = _footnote(bool(normalized.get("noise")))
    result = {
        "config": normalized, "initial_matrix": copy.deepcopy(base.get("initial", [])),
        "rows": [], "table_headers": list(TABLE_HEADERS), "table_rows": [],
        "footnote": footnote, "status": "invalid", "message": "",
    }
    base_summary = base.get("summary", {})
    if base_summary.get("status") in ("invalid", "algorithm_error") or not result["initial_matrix"]:
        result["status"] = base_summary.get("status", "invalid")
        result["message"] = base_summary.get("message", "Could not generate an initial state for comparison.")
        return result

    frozen = copy.deepcopy(result["initial_matrix"])
    target_count = base_summary.get("target_count", 0)
    rows = []
    for key, implementation in list(simulator.ALGORITHMS.items()):
        label = _algorithm_label(key, implementation)
        if not _supports_pattern(key, normalized["pattern"]):
            rows.append(_row(key, label, {
                "status": "skipped", "target_count": target_count,
                "message": f"{label} does not support this target pattern in the demo and was skipped.",
            }, None, None, target_count))
            continue
        if deadline is not None and time.monotonic() >= deadline:
            rows.append(_row(key, label, {"status": "not_run", "target_count": target_count,
                "message": "The computation time budget was reached before this algorithm could run."}, None, None, target_count))
            continue
        candidate = copy.deepcopy(normalized)
        candidate.update(algorithm=key, initial_mode="manual", initial_matrix=copy.deepcopy(frozen))
        if key not in simulator.MULTI_TWEEZER_ALGORITHMS:
            candidate["tweezer_count"] = 1
        try:
            simulation = simulator.simulate(candidate)
            moves, distance = _successful_transports(simulation, normalized["spacing_um"])
            summary = dict(simulation.get("summary", {}))
            if not simulation.get("initial") and not simulation.get("frames") and summary.get("status") in ("algorithm_error", "invalid"):
                # A worker may fail before it reports an initial state. The known
                # target is retained, but unobserved execution metrics are unknown.
                summary.update(target_count=target_count, filled=None, losses=None,
                               simulated_time=None, executed_batches=None, max_active_tweezers=None)
                moves = distance = None
            rows.append(_row(key, label, summary, moves, distance, target_count,
                             candidate.get("tweezer_count", 1)))
        except Exception as error:
            rows.append(_row(key, label, {
                "status": "algorithm_error", "target_count": target_count,
                "message": f"{label} comparison failed: {type(error).__name__}: {error}.",
            }, None, None, target_count, candidate.get("tweezer_count", 1)))
        if on_progress:
            on_progress(key)
    partial = any(row['status'] == 'not_run' for row in rows)
    result.update(rows=rows, table_rows=_table_rows(rows), status="partial" if partial else "complete",
                  message=f"Executed {sum(row['status'] not in ('skipped', 'not_run') for row in rows)} algorithms from the same initial state.")
    return result
