"""Capacity and point-trajectory safety scheduling around native AOD commands.

This model checks synchronous, straight, one-lattice-step trajectories and the
original library's crossed-tone rules. It does not model beam waists, force
profiles, cooling, or free motion of a turned-off/empty transport tweezer.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

from atommovr.utils.Move import Move
from atommovr.utils.aod_timing import _has_colliding_tones
from atommovr.utils.errormodels import ZeroNoise
from atommovr.utils.failure_policy import FailureEvent
from atommovr.utils.move_utils import get_AOD_cmds_from_move_list, get_move_list_from_AOD_cmds


@dataclass
class Schedule:
    batches: list[list[Move]] = field(default_factory=list)
    native_indices: list[int] = field(default_factory=list)
    blocked_reason: str | None = None
    native_batches: int = 0
    skipped_empty_batches: int = 0


def source(move: Move) -> tuple[int, int]:
    return int(move.from_row), int(move.from_col)


def destination(move: Move) -> tuple[int, int]:
    return int(move.to_row), int(move.to_col)


def _validate_moves(array, moves):
    n_rows, n_cols = array.matrix.shape[:2]
    for move in moves:
        coordinates = (move.from_row, move.from_col, move.to_row, move.to_col)
        if any(isinstance(value, (bool, np.bool_))
               or not isinstance(value, (int, float, np.integer, np.floating))
               or not np.isfinite(value) or int(value) != value for value in coordinates):
            raise ValueError("Tweezer positions must be integer grid coordinates")
        start, end = source(move), destination(move)
        if any(not (0 <= point[0] < n_rows and 0 <= point[1] < n_cols) for point in (start, end)):
            raise ValueError("A tweezer trajectory leaves the array bounds")
        if abs(end[0] - start[0]) > 1 or abs(end[1] - start[1]) > 1:
            raise ValueError("The native batch contains a move longer than one grid step; AOD direction signs cannot silently shorten it")


def aod_closure(array, moves: list[Move]) -> list[Move]:
    """Return every physical Cartesian intersection, including empty and hold."""
    if not moves:
        return []
    _validate_moves(array, moves)
    horizontal, vertical, compatible = get_AOD_cmds_from_move_list(array.matrix, moves)
    if not compatible:
        raise ValueError("The same source row or column requires conflicting AOD commands")
    closed = get_move_list_from_AOD_cmds(horizontal, vertical)
    for i, move in enumerate(closed, 1):
        move.tweezer_id = i
    return closed


def minimum_relative_distance_squared(first: Move, second: Move) -> float:
    """Analytic minimum for two point trajectories at the SAME t in [0,1]."""
    offset = np.asarray(source(first), dtype=float) - np.asarray(source(second), dtype=float)
    relative_velocity = (np.asarray(destination(first), dtype=float) - np.asarray(source(first), dtype=float)
                         - np.asarray(destination(second), dtype=float) + np.asarray(source(second), dtype=float))
    norm = float(relative_velocity @ relative_velocity)
    at = float(np.clip(-(offset @ relative_velocity) / norm, 0, 1)) if norm else 0.0
    closest = offset + at * relative_velocity
    return float(closest @ closest)


def _point_segment_distance_squared(move: Move, point: tuple[int, int]) -> float:
    offset = np.asarray(source(move), dtype=float) - np.asarray(point, dtype=float)
    velocity = np.asarray(destination(move), dtype=float) - np.asarray(source(move), dtype=float)
    norm = float(velocity @ velocity)
    at = float(np.clip(-(offset @ velocity) / norm, 0, 1)) if norm else 0.0
    closest = offset + at * velocity
    return float(closest @ closest)


def intended_after(array, moves: list[Move]) -> np.ndarray:
    """Apply simultaneous intended transfers without silently erasing overlaps."""
    before = array.matrix.astype(np.int16)
    after = before.copy()
    _validate_moves(array, moves)
    seen = set()
    for move in moves:
        start, end = source(move), destination(move)
        if start in seen:
            raise ValueError("The native batch contains duplicate source sites")
        seen.add(start)
        if before[start[0], start[1], 0]:
            after[start[0], start[1], 0] -= 1
            after[end[0], end[1], 0] += 1
    if np.any(after < 0) or np.any(after > 1):
        raise ValueError("Native batch destinations overlap or dependencies cannot be satisfied simultaneously")
    return after.astype(np.uint8)


def check_batch(array, moves: list[Move], capacity: int, *, protect_pickup_failures=False,
                expected_sources: set[tuple[int, int]] | None = None):
    """Check BEFORE execution; validate the full closure with native ZeroNoise.

    Returns (safe, reason, closed_commands, noiseless_after). Expected sources
    constrain ghost intersections from picking up atoms unexpectedly.
    """
    try:
        closed = aod_closure(array, moves)
        if len(closed) > capacity:
            return False, "The full AOD intersection count exceeds the tweezer limit", closed, None
        horizontal, vertical, _ = get_AOD_cmds_from_move_list(array.matrix, closed)
        if _has_colliding_tones(vertical, horizontal):
            return False, "AOD frequency commands produce crossing or merging collisions", closed, None
        # Evaluate the analytic same-time minimum in bulk; this includes empty
        # and hold intersections and avoids per-point Python loops on N=24.
        starts = np.asarray([source(move) for move in closed], dtype=float).reshape(-1, 2)
        velocities = np.asarray([destination(move) for move in closed], dtype=float).reshape(-1, 2) - starts
        offsets = starts[:, None, :] - starts[None, :, :]
        relative_velocities = velocities[:, None, :] - velocities[None, :, :]
        norms = np.sum(relative_velocities ** 2, axis=2)
        at = np.clip(np.divide(-np.sum(offsets * relative_velocities, axis=2), norms,
                               out=np.zeros_like(norms), where=norms != 0), 0, 1)
        distances = np.sum((offsets + at[:, :, None] * relative_velocities) ** 2, axis=2)
        if np.any(np.triu(distances < 1e-12, 1)):
            return False, "A collision occurs between tweezers during continuous transport", closed, None
        occupied = {tuple(int(value) for value in point) for point in np.argwhere(array.matrix[:, :, 0] > 0)}
        movers = {source(move) for move in closed if source(move) != destination(move) and source(move) in occupied}
        stationary = occupied if protect_pickup_failures else occupied - movers
        for move in closed:
            if source(move) == destination(move):
                continue
            if expected_sources is not None and source(move) in occupied and source(move) not in expected_sources:
                return False, "An empty-site tweezer would unintentionally transport a residual atom outside the plan", closed, None
            points = np.asarray(list(stationary - {source(move)}), dtype=float).reshape(-1, 2)
            offset = np.asarray(source(move), dtype=float) - points
            velocity = np.asarray(destination(move), dtype=float) - np.asarray(source(move), dtype=float)
            at = np.clip(-np.sum(offset * velocity, axis=1) / float(velocity @ velocity), 0, 1)
            if np.any(np.sum((offset + at[:, None] * velocity) ** 2, axis=1) < 1e-12):
                return False, "A complete transport path crosses a stationary occupied site", closed, None
        expected = intended_after(array, closed)
        trial = copy.deepcopy(array)
        trial.error_model = ZeroNoise()
        tested = copy.deepcopy(closed)
        trial.move_atoms(tested, [], [])
        if any(int(move.fail_event) not in (int(FailureEvent.SUCCESS), int(FailureEvent.NO_ATOM)) for move in tested):
            return False, "The library's noise-free validation detected a collision or failed move", closed, None
        if not np.array_equal(trial.matrix, expected) or int(trial.matrix.sum()) != int(array.matrix.sum()):
            return False, "Library validation detected overlap loss or unintended displacement", closed, None
        return True, "", closed, trial.matrix.copy()
    except Exception as error:
        return False, str(error), [], None


def _candidate(array, requested, pending, capacity, protect_pickup_failures):
    try:
        closed = aod_closure(array, requested)
    except ValueError as error:
        return False, str(error), [], None
    for move in closed:
        start = source(move)
        if array.matrix[start[0], start[1], 0] and start != destination(move):
            if start not in pending or destination(move) != destination(pending[start]):
                return False, "Additional AOD intersections would cause unintended atom displacement", closed, None
    return check_batch(array, closed, capacity, protect_pickup_failures=protect_pickup_failures,
                       expected_sources=set(pending))


def schedule_moves(array, native_batches: list[list[Move]], capacity: int, *,
                   protect_pickup_failures=False, max_batches=2000, max_moves=50_000) -> Schedule:
    """Keep safe native rectangles, otherwise partition with vacancy dependencies.

    Empty native commands are not standalone tasks during partitioning, but
    every empty/holding intersection implied by an EXECUTED AOD rectangle counts
    toward capacity. Atomic transfers never disappear silently.
    """
    schedule = Schedule(native_batches=len(native_batches))
    ideal = copy.deepcopy(array)
    ideal.error_model = ZeroNoise()
    total_commands = 0

    def append(batch, after, native_index):
        nonlocal total_commands
        if len(schedule.batches) >= max_batches or total_commands + len(batch) > max_moves:
            schedule.blocked_reason = "The complete AOD schedule exceeds the demo resource limit. Reduce the array or target size"
            return False
        for i, move in enumerate(batch, 1):
            move.tweezer_id = i
            move.expected_occupied = bool(ideal.matrix[move.from_row, move.from_col, 0])
        schedule.batches.append(batch)
        schedule.native_indices.append(native_index)
        total_commands += len(batch)
        ideal.matrix = after.copy()
        return True

    for native_index, native in enumerate(native_batches):
        try:
            # Native requested transfers define intent. An occupied extra
            # crossed-AOD intersection must never expand that intent.
            aod_closure(ideal, native)
            expected_end = intended_after(ideal, native)
        except ValueError as error:
            schedule.blocked_reason = f"The native batch cannot execute safely: {error}"
            return schedule
        pending = {source(move): move for move in native if source(move) != destination(move)
                   and ideal.matrix[move.from_row, move.from_col, 0]}
        safe, _, closed, after = _candidate(
            ideal, native, pending, capacity, protect_pickup_failures)
        if safe:
            if closed and not append(closed, after, native_index):
                return schedule
            continue
        if not pending:
            schedule.skipped_empty_batches += 1
            continue
        while pending:
            safe, reason, chosen, after = _candidate(
                ideal, list(pending.values()), pending, capacity, protect_pickup_failures)
            if not safe:
                chosen = []
                for seed in list(pending.values()):
                    safe, reason, selected, after = _candidate(
                        ideal, [seed], pending, capacity, protect_pickup_failures)
                    if not safe:
                        continue
                    requested = [seed]
                    for addition in list(pending.values()):
                        if addition in requested:
                            continue
                        grows, _, expanded, grown_after = _candidate(
                            ideal, requested + [addition], pending, capacity, protect_pickup_failures)
                        if grows:
                            requested.append(addition)
                            selected, after = expanded, grown_after
                    chosen = selected
                    break
                if not chosen:
                    schedule.blocked_reason = (
                        "No vacant destination can be reached safely: a swap, dependency cycle, or stationary obstacle is present. "
                        f"The current tweezer limit is {capacity}. The batch was not split unsafely. {reason}"
                    )
                    return schedule
            completed = {source(move) for move in chosen if source(move) in pending
                         and destination(move) == destination(pending[source(move)])}
            if not completed:
                schedule.blocked_reason = "Scheduling could not advance the pending moves and was stopped"
                return schedule
            if not append(chosen, after, native_index):
                return schedule
            for point in completed:
                pending.pop(point)
        if not np.array_equal(ideal.matrix, expected_end):
            schedule.blocked_reason = "Atom positions after splitting differ from the native batch's intent; execution was stopped"
            return schedule
    return schedule
