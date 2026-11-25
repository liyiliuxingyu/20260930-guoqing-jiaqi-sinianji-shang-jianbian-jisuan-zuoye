#!/usr/bin/env python3
"""Package this project, excluding reproducible build files, and verify extraction."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from verify_package import ROOT, files

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT.parent/"简便计算_续作工程.zip")
    args=parser.parse_args()
    dest=args.output.expanduser().resolve()
    if dest==ROOT or ROOT in dest.parents:
        raise ValueError("The output ZIP must be outside the project directory.")
    dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/"tools/verify_package.py"),"--write"],check=True)
    subprocess.run([sys.executable,str(ROOT/"tools/verify_package.py")],check=True)
    all_files=files()+[ROOT/"MANIFEST.json"]
    with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(all_files):
            z.write(p,Path(ROOT.name)/p.relative_to(ROOT))
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None, "ZIP CRC failed"
        for name in z.namelist():
            p=Path(name)
            if p.is_absolute() or ".." in p.parts:raise ValueError("Unsafe archive path")
        with tempfile.TemporaryDirectory(prefix="jianbian-unzip-") as d:
            z.extractall(d)
            extracted=Path(d)/ROOT.name
            subprocess.run([sys.executable,str(extracted/"tools/verify_package.py")],check=True)
    print("ZIP: "+str(dest))
    print("Files: "+str(len(all_files)))
    print("Bytes: "+str(dest.stat().st_size))
    print("SHA256: "+hashlib.sha256(dest.read_bytes()).hexdigest())

if __name__=="__main__":
    main()

