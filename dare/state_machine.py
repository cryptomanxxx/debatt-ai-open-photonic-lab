"""DARE-002: deterministic offline recommendations, never executes actions."""
from dataclasses import dataclass, field, asdict
import json

@dataclass
class Task:
    approved: bool = False
    scope: tuple = ()
    dependencies: tuple = ()
    head: str = ""
    ci_head: str = ""
    ci: str = "unknown"
    review_head: str = ""
    review: str = "unknown"
    threads: int = -1
    quota: str = "unknown"
    cost_verified: bool = False
    paid_fallback_disabled: bool = False
    stopped: bool = False
    leased: bool = False
    retries: int = 0
    merged: bool = False
    archive_verified: bool = False
    sequence: int = 0

@dataclass
class Engine:
    tasks: dict = field(default_factory=dict)
    stopped: bool = False

    def snapshot(self):
        return json.dumps({"tasks": {k: asdict(v) for k,v in self.tasks.items()},
                           "stopped": self.stopped}, sort_keys=True)

    @classmethod
    def restore(cls, raw):
        data = json.loads(raw)
        return cls({k: Task(**v) for k,v in data["tasks"].items()}, data["stopped"])

    def observe(self, task_id, sequence, **changes):
        """Synthetic trusted snapshots only; not an external event parser."""
        t = self.tasks[task_id]
        if type(sequence) is not int or sequence <= t.sequence:
            return False
        if not changes.keys() <= set(asdict(t)) - {"sequence", "approved", "scope", "dependencies"}:
            raise ValueError("unexpected observation fields")
        # A head change invalidates prior checks, even when the new snapshot
        # contains check data; require a later observation for the new head.
        if "head" in changes and changes["head"] != t.head:
            changes.update(ci="unknown", ci_head="", review="unknown",
                           review_head="", threads=-1, archive_verified=False)
        for k,v in changes.items():
            setattr(t,k,v)
        t.sequence = sequence
        return True

    def _graph_valid(self):
        visited, active = set(), set()
        def visit(k):
            if k in active or k not in self.tasks:
                return False
            if k in visited:
                return True
            active.add(k)
            if not all(visit(d) for d in self.tasks[k].dependencies):
                return False
            active.remove(k)
            visited.add(k)
            return True
        return all(visit(k) for k in self.tasks)

    def recommend(self, task_id):
        """Return one advisory label; no execution adapter or credentials."""
        t = self.tasks[task_id]
        if self.stopped is not False or t.stopped is not False:
            return "STOPPED"
        if not self._graph_valid():
            return "BLOCK_GRAPH"
        if t.approved is not True or not t.scope:
            return "BLOCK_SCOPE"
        if t.merged is True:
            return "COMPLETE" if t.archive_verified is True else "CHECK_ARCHIVE"
        if not all(self.tasks[d].merged is True and
                   self.tasks[d].archive_verified is True for d in t.dependencies):
            return "WAIT_DEPENDENCY"
        if (t.quota != "available" or t.cost_verified is not True
                or t.paid_fallback_disabled is not True):
            return "BLOCK_COST"
        if type(t.retries) is not int or not 0 <= t.retries < 3:
            return "BLOCK_RETRIES"
        if any(v.leased is not False for v in self.tasks.values()):
            return "WAIT_LEASE"
        if not t.head:
            return "PROPOSE_IMPLEMENTATION"
        if t.ci_head != t.head or t.review_head != t.head:
            return "WAIT_CURRENT_HEAD"
        if t.ci == "failed" or t.review == "findings":
            return "PROPOSE_CORRECTION"
        if t.ci != "passed" or t.review != "clear" or type(t.threads) is not int or t.threads != 0:
            return "WAIT_CHECKS"
        return "REQUEST_HUMAN_MERGE"

    def next_task(self):
        for k in sorted(self.tasks):
            action = self.recommend(k)
            if action in {"PROPOSE_IMPLEMENTATION", "PROPOSE_CORRECTION",
                          "REQUEST_HUMAN_MERGE", "CHECK_ARCHIVE"}:
                return k, action
        return None
