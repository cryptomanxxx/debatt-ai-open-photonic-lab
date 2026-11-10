"""Regression tests for tools/check_gds_archive.py.

Each case builds a throw-away git repository with a copy of the checker, a
committed base release, and one change, then runs the checker with --base and
compares its exit code with the expected one. Run with:

    python tools/test_check_gds_archive.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

CHECKER = Path(__file__).resolve().parent / "check_gds_archive.py"
GEN = {"script": "layout/x.py", "commit": "abc", "environment": "layout/req.txt"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release(repo, name, files, generator=GEN, listed=None):
    folder = repo / "gds" / name
    folder.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (folder / fname).write_bytes(content)
    if listed is None:
        listed = {f: sha(folder / f) for f in files}
    prov = {"design": "t", "version": "1", "date": "2026-11-10", "status": "exploratory",
            "pdk": "generic", "generator": generator, "released_to": "nobody",
            "files": listed}
    (folder / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")
    return folder


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp):
    repo = Path(tmp)
    (repo / "tools").mkdir()
    shutil.copy(CHECKER, repo / "tools" / CHECKER.name)
    (repo / "gds").mkdir()
    (repo / "gds" / "README.md").write_text("# index\n")
    (repo / "results").mkdir()
    (repo / "results" / "working.gds").write_bytes(b"WORK")
    release(repo, "rel1", {"a.gds": b"AAAA"})
    release(repo, "rel-µ", {"coupler-23µm.gds": b"MUMU"})
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "test")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


def run(repo, base="HEAD"):
    return subprocess.run([sys.executable, "-I", str(repo / "tools" / CHECKER.name),
                           "--base", base], capture_output=True).returncode


def case_unchanged(repo):
    pass


def case_new_release(repo):
    release(repo, "rel2", {"b.gds": b"BBBB"})


def case_external_generator(repo):
    release(repo, "rel2", {"b.gds": b"BBBB"}, generator={"external": "made elsewhere"})


def case_index_readme_edit(repo):
    (repo / "gds" / "README.md").write_text("# index, edited\n")


def case_release_readme_unlisted(repo):
    folder = release(repo, "rel2", {"b.gds": b"BBBB"})
    (folder / "README.md").write_text("# release notes\n")


def case_empty_generator(repo):
    release(repo, "rel2", {"b.gds": b"BBBB"}, generator={})


def case_modified_with_new_checksum(repo):
    release(repo, "rel1", {"a.gds": b"ZZZZ"})


def case_deleted_release(repo):
    shutil.rmtree(repo / "gds" / "rel1")


def case_modified_non_ascii(repo):
    release(repo, "rel-µ", {"coupler-23µm.gds": b"CHANGED"})


def case_path_outside_folder(repo):
    release(repo, "rel2", {}, listed={"../../results/working.gds": sha(repo / "results" / "working.gds")})


def case_no_layout_file(repo):
    release(repo, "rel2", {"notes.txt": b"hi"})


def case_unlisted_uppercase_gds(repo):
    folder = release(repo, "rel2", {"b.gds": b"BBBB"})
    (folder / "fabrication.GDS").write_bytes(b"FAB")


def case_unlisted_other_file(repo):
    folder = release(repo, "rel2", {"b.gds": b"BBBB"})
    (folder / "notes.txt").write_bytes(b"hi")


def case_subfolder(repo):
    folder = release(repo, "rel2", {"b.gds": b"BBBB"})
    (folder / "sub").mkdir()


def case_symlink_in_working_tree(repo):
    folder = repo / "gds" / "rel2"
    folder.mkdir()
    os.symlink("../../results/working.gds", folder / "chip.gds")
    release(repo, "rel2", {}, listed={"chip.gds": sha(repo / "results" / "working.gds")})


CASES = [
    (case_unchanged, 0), (case_new_release, 0), (case_external_generator, 0),
    (case_index_readme_edit, 0), (case_release_readme_unlisted, 0),
    (case_empty_generator, 1), (case_modified_with_new_checksum, 1),
    (case_deleted_release, 1), (case_modified_non_ascii, 1),
    (case_path_outside_folder, 1), (case_no_layout_file, 1),
    (case_unlisted_uppercase_gds, 1), (case_unlisted_other_file, 1),
    (case_subfolder, 1), (case_symlink_in_working_tree, 1),
]


def symlink_committed_at_base():
    """A symlink that is already in git at the base revision must also fail."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = make_repo(tmp)
        case_symlink_in_working_tree(repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "symlink release")
        return run(repo)


def main():
    failures = 0
    for func, expected in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp)
            func(repo)
            code = run(repo)
        ok = code == expected
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {func.__name__}: exit {code}, expected {expected}")
    code = symlink_committed_at_base()
    failures += code != 1
    print(f"{'ok  ' if code == 1 else 'FAIL'} symlink_committed_at_base: exit {code}, expected 1")
    print(f"{len(CASES) + 1 - failures}/{len(CASES) + 1} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
