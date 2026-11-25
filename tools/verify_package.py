#!/usr/bin/env python3
"""Verify every archived file against MANIFEST.json, or explicitly refresh it.
No third-party Python package is required. Generated build/ files are excluded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"
EXCLUDED_DIRS = {"build", "__pycache__", ".venv", ".git", ".tex-cache"}
EXCLUDED_FILES = {"MANIFEST.json", ".DS_Store"}

def files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file()
                  and not EXCLUDED_DIRS.intersection(p.relative_to(ROOT).parts)
                  and p.name not in EXCLUDED_FILES)

def record(p):
    return {"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

def references():
    checked, unresolved = [], []
    pattern = re.compile(r"\\(?:input|include|includegraphics)(?:\[[^\]]*\])?\{([^{}]+)\}")
    for p in (ROOT/"src").glob("*.tex"):
        for name in pattern.findall(p.read_text(encoding="utf-8")):
            if "\\" in name or "#" in name:
                unresolved.append({"file":p.name,"reference":name,"reason":"dynamic reference"})
                continue
            candidates = [p.parent/name, ROOT/name]
            if not Path(name).suffix:
                candidates += [Path(str(c)+ext) for c in candidates for ext in (".tex",".pdf",".png",".jpg")]
            if not any(c.is_file() for c in candidates):
                unresolved.append({"file":p.name,"reference":name,"reason":"missing"})
            else:
                checked.append({"file":p.name,"reference":name})
    return checked, unresolved

def check_required():
    path = ROOT / "REQUIRED_FILES.json"
    if not path.is_file():
        raise RuntimeError("REQUIRED_FILES.json is missing; cannot refresh a complete archive.")
    required = json.loads(path.read_text(encoding="utf-8"))["paths"]
    missing = [rel for rel in required if not (ROOT / rel).is_file() or (ROOT / rel).stat().st_size == 0]
    if missing:
        raise RuntimeError("Required project files missing or empty:\n" + "\n".join(missing))


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--write",action="store_true",help="Refresh hashes after an intentional reviewed edit")
    args=a.parse_args()
    check_required()
    if args.write:
        entries=[record(p) for p in files()]
        MANIFEST.write_text(json.dumps({"schema":1,"files":entries},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("Manifest written: " + str(len(entries)) + " files.")
        return
    if not MANIFEST.is_file():
        raise RuntimeError("MANIFEST.json is missing.")
    expected=json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    errors=[]
    expected_paths=set()
    for item in expected:
        rel=Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            errors.append("Unsafe manifest path: "+item["path"]);continue
        expected_paths.add(rel.as_posix())
        p=ROOT/rel
        if not p.is_file():errors.append("Missing: "+item["path"]);continue
        actual=record(p)
        if actual["sha256"]!=item["sha256"] or actual["bytes"]!=item["bytes"]:
            errors.append("Changed: "+item["path"])
    extras=[p.relative_to(ROOT).as_posix() for p in files() if p.relative_to(ROOT).as_posix() not in expected_paths]
    errors += ["Unlisted: "+x for x in extras]
    checked,unresolved=references()
    errors += ["Unresolved source reference: "+str(x) for x in unresolved]
    for p in (ROOT/"history").rglob("*.zip"):
        with zipfile.ZipFile(p) as z:
            bad=z.testzip()
            if bad:errors.append("Historical ZIP CRC failed: "+str(p)+":"+bad)
    if errors:
        print("\n".join(errors),file=sys.stderr);sys.exit(1)
    print(json.dumps({"status":"passed","hashed_files":len(expected),
                      "source_references_checked":len(checked),
                      "missing_or_changed_files":0,"unresolved_source_references":0},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,RuntimeError,zipfile.BadZipFile) as e:
        print(str(e),file=sys.stderr);sys.exit(1)

