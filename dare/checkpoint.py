"""Offline single-writer qualification interface; no execution adapter."""
from dataclasses import dataclass
from pathlib import Path
import os
from guarded_gate import GuardedGate
from persistence import load_snapshot, save_snapshot


@dataclass(frozen=True)
class Sequenced:
    sequence: int
    value: object


class Checkpoint:
    """Trusted local directory; interrupted transactions require manual repair."""
    def __init__(self, path, required_checks, archive_policy):
        self.path = Path(path)
        self.marker = self.path.with_name(self.path.name + ".pending")
        self.required_checks = required_checks
        self.archive_policy = archive_policy

    def _sync_dir(self):
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _begin(self):
        with self.marker.open("x", encoding="utf-8") as f:
            f.write("STOP: reconcile snapshot before resuming\n")
            f.flush()
            os.fsync(f.fileno())
        self._sync_dir()

    def _end(self):
        self.marker.unlink()
        self._sync_dir()

    def _gate(self):
        if self.marker.exists() or self.marker.is_symlink():
            raise ValueError("unreconciled transaction")
        return GuardedGate(load_snapshot(self.path), self.required_checks,
                           self.archive_policy)

    @staticmethod
    def _current(engine, supplied):
        return {key: ev.value for key, ev in supplied.items()
                if key in engine.tasks and type(ev) is Sequenced
                and type(ev.sequence) is int
                and ev.sequence == engine.tasks[key].sequence}

    def recommend(self, task, now, cost, reviews, archives):
        try:
            gate = self._gate()
            return gate.recommend(task, now, self._current(gate.engine, cost),
                                  self._current(gate.engine, reviews), archives)
        except (OSError, ValueError, TypeError, AttributeError, KeyError, RecursionError):
            return "BLOCK_CHECKPOINT"

    def reserve(self, task, now, cost, reviews, archives):
        gate = self._gate()
        if not gate.reserve_correction(task, now, self._current(gate.engine, cost),
                                       self._current(gate.engine, reviews), archives):
            return False
        self._begin()
        save_snapshot(self.path, gate.engine)
        self._end()
        return True

    def recover(self, task, evidence, now):
        gate = self._gate()
        # Invalid recovery requests may leave a conservative marker if the
        # operation raises; a normal rejection makes no snapshot mutation.
        self._begin()
        result = gate.recover(task, evidence, now, self.path)
        self._end()
        return result

    def stop(self):
        gate = self._gate()
        self._begin()
        gate.engine.stopped = True
        save_snapshot(self.path, gate.engine)
        self._end()
