"""Import only the exact reviewed AG003 artifact bytes; never execute source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "circuit_sim.py": (11752, "959f3da12351c8ad9f02cb5129f5ea4f03c450b28e77f159f12ca11568d5804b"),
    "params.py": (9465, "7fe613c806ad39f29a44131ee03d6bebc968e558dfd023ed3589be890338d144"),
    "physics_model.py": (25790, "5b4fee09a4570451a06654e5aabd4ea1f5fbe8b0a89d7977e3400f5ade288599"),
    "report.json": (84104, "67bf8791ca8af9f810f9b8baba750ea2af626f62b6850c24e6ba7d911a3816e1"),
    "run_all.py": (10614, "f6b757d30be90bff43be4d77e86e82e44d92d196a227ca88d0f00a7628b30b5a"),
    "sweep.py": (13747, "8939fa7f0d267e3001d3ea21054ebb9ac1ddce9ac452ec2d88d1f71dca327f64"),
    "train_sim.py": (9378, "ddfaac05be2933bab4ad3303b066fb6c27fbd7a8cc053b9586d1b6614cc0162e"),
}

def verify(source, expected=EXPECTED):
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Invalid source directory")
    if {p.name for p in source.iterdir()} != set(expected):
        raise ValueError("Unexpected or missing artifact entries")
    files = {}
    for name, (size, digest) in expected.items():
        p = source / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
            raise ValueError(f"Invalid file: {name}")
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Digest mismatch: {name}")
        files[name] = data
    return files

def import_snapshot(source, output, expected=EXPECTED):
    files = verify(source, expected)
    output.mkdir(parents=False, exist_ok=False)
    try:
        for name, data in files.items():
            (output / name).write_bytes(data)
        verify(output, expected)
    except Exception:
        shutil.rmtree(output)
        raise

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.output is None:
        verify(a.source)
    else:
        import_snapshot(a.source, a.output)
    print(json.dumps({"verified_files": len(EXPECTED),
                      "total_bytes": sum(v[0] for v in EXPECTED.values()),
                      "source_executed": False}))

if __name__ == "__main__":
    main()
