"""DARE-002D: offline guarded recommendations and explicit recovery.

Single trusted operator, synthetic evidence, no live execution.
"""
from dataclasses import dataclass
from evidence_gate import EvidenceGate, fresh
from persistence import validated_restore, save_snapshot


@dataclass(frozen=True)
class RecoveryEvidence:
    task: str
    head: str
    sequence: int
    attempt: int
    observed: int
    worker_stopped: bool
    reconciled: bool
    operator_approved: bool


class GuardedGate(EvidenceGate):
    def archived(self, task_id, archives):
        # The validated graph is acyclic before recommend calls this.
        memo = {}
        active = set()

        def walk(key):
            if key in active:
                return False
            if key in memo:
                return memo[key]
            active.add(key)
            task = self.engine.tasks[key]
            value = (task.approved is True and bool(task.scope)
                     and task.stopped is False
                     and super(GuardedGate, self).archived(key, archives)
                     and all(walk(d) for d in task.dependencies))
            active.remove(key)
            memo[key] = value
            return value
        return walk(task_id)

    def recommend(self, task_id, now, cost_observed, reviews, archives):
        try:
            if task_id not in self.engine.tasks:
                return "BLOCK_STATE"
            return super().recommend(task_id, now, cost_observed, reviews, archives)
        except (ValueError, TypeError, AttributeError, KeyError, OSError, RecursionError):
            return "BLOCK_EVIDENCE"

    def recover(self, task_id, evidence, now, snapshot_path):
        """Explicit operator reconciliation; no automatic retry or resume.

        A new persisted snapshot is written before replacing in-memory state.
        Any ambiguous write failure must stop the caller and require reload.
        """
        try:
            candidate = validated_restore(self.engine.snapshot())
            t = candidate.tasks[task_id]
            valid = (type(evidence) is RecoveryEvidence
                     and evidence.task == task_id and bool(t.head)
                     and evidence.head == t.head
                     and type(evidence.sequence) is int
                     and evidence.sequence > t.sequence
                     and type(evidence.attempt) is int
                     and evidence.attempt == t.retries and t.retries > 0
                     and fresh(evidence.observed, now)
                     and evidence.worker_stopped is True
                     and evidence.reconciled is True
                     and evidence.operator_approved is True
                     and t.leased is True and not t.merged)
        except (ValueError, TypeError, AttributeError, KeyError, RecursionError):
            return False
        if not valid:
            return False
        t.leased = False
        t.sequence = evidence.sequence
        t.ci = t.review = "unknown"
        t.ci_head = t.review_head = ""
        t.threads = -1
        t.cost_verified = False
        t.quota = "unknown"
        # Preserve retries and stop flags. External cost/check evidence
        # must be reconciled separately before further recommendations.
        try:
            save_snapshot(snapshot_path, candidate)
        except (OSError, ValueError):
            self.engine.stopped = True
            raise
        self.engine.tasks = candidate.tasks
        self.engine.stopped = candidate.stopped
        return True
