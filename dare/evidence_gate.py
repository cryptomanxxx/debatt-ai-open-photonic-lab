"""DARE-002C: conservative offline evidence gates over the legacy engine."""
from dataclasses import dataclass
from persistence import verify_archive, validated_restore

MAX_AGE = 300  # Synthetic seconds; not a production policy.
MAX_RETRIES = 3


@dataclass(frozen=True)
class ReviewEvidence:
    head: str
    observed: int
    checks: dict
    review: str
    threads: int
    complete: bool


@dataclass(frozen=True)
class ArchiveEvidence:
    task: str
    head: str
    run: str
    root: object
    manifest: dict


def fresh(observed, now):
    return (type(observed) is int and type(now) is int
            and 0 <= observed <= now and now - observed <= MAX_AGE)


class EvidenceGate:
    """Trusted synthetic inputs only; no external action adapter.

    Policies and evidence are supplied anew after restart. Legacy archive
    booleans alone never release dependencies through this interface.
    """
    def __init__(self, engine, required_checks, archive_policy):
        self.engine = engine
        self.required_checks = required_checks
        self.archive_policy = archive_policy

    def archived(self, task_id, archives):
        task = self.engine.tasks[task_id]
        ev = archives.get(task_id)
        policy = self.archive_policy.get(task_id)
        if not task.merged or not task.head or not ev or not policy:
            return False
        run, expected = policy
        return (bool(run) and ev.task == task_id and ev.head == task.head
                and ev.run == run and verify_archive(ev.root, expected, ev.manifest))

    def recommend(self, task_id, now, cost_observed, reviews, archives):
        # Validate a copy; never trust legacy archive or review booleans.
        try:
            copy = validated_restore(self.engine.snapshot())
        except (ValueError, TypeError, RecursionError):
            return "BLOCK_STATE"
        task = copy.tasks[task_id]
        if copy.stopped or task.stopped:
            return "STOPPED"
        for key, value in copy.tasks.items():
            value.archive_verified = self.archived(key, archives)
        if task.merged:
            return copy.recommend(task_id)
        if not fresh(cost_observed.get(task_id), now):
            task.cost_verified = False
        if task.head:
            ev = reviews.get(task_id)
            required = self.required_checks.get(task_id)
            task.ci = task.review = "unknown"
            task.ci_head = task.review_head = ""
            task.threads = -1
            if (ev and required and ev.head == task.head
                    and fresh(ev.observed, now) and ev.complete is True
                    and type(ev.checks) is dict and set(ev.checks) == required
                    and all(v in ("passed", "failed", "pending", "skipped")
                            for v in ev.checks.values())
                    and ev.review in ("clear", "findings", "pending")
                    and type(ev.threads) is int and ev.threads >= 0):
                task.ci_head = task.review_head = task.head
                states = ev.checks.values()
                task.ci = ("failed" if "failed" in states else
                           "passed" if all(v == "passed" for v in states)
                           else "pending")
                task.review = ev.review
                task.threads = ev.threads
        # A retry ceiling blocks further correction/implementation, not a
        # human merge recommendation when all checks eventually pass.
        retries = task.retries
        task.retries = 0
        action = copy.recommend(task_id)
        if action in ("PROPOSE_IMPLEMENTATION", "PROPOSE_CORRECTION") and retries >= MAX_RETRIES:
            return "BLOCK_RETRIES"
        return action

    def reserve_correction(self, task_id, now, cost_observed, reviews, archives):
        """Reserve one synthetic correction attempt; single writer only."""
        if self.recommend(task_id, now, cost_observed, reviews, archives) != "PROPOSE_CORRECTION":
            return False
        task = self.engine.tasks[task_id]
        task.retries += 1
        task.leased = True
        return True

    def finish_correction(self, task_id):
        """Release synthetic lease, invalidate checks until re-observed."""
        task = self.engine.tasks[task_id]
        if not task.leased:
            return False
        task.leased = False
        task.ci = task.review = "unknown"
        task.ci_head = task.review_head = ""
        task.threads = -1
        return True
