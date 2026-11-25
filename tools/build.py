#!/usr/bin/env python3
"""Build the current project into build/, preserving the delivered outputs/.
Usage: python tools/build.py --target all
Requires Python 3.10+, XeLaTeX/TeX Live, PyMuPDF and Pillow.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "简便计算_A4_题目.tex",
    "简便计算_A4答案_新版.tex",
    "简便计算_A4合订本_新版.tex",
    "简便计算_题目4页.tex",
]

def run(args, *, env=None, cwd=None, timeout=120):
    proc = subprocess.run(args, env=env, cwd=cwd, text=True,
                          encoding="utf-8", errors="replace",
                          capture_output=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError("Command failed: " + " ".join(map(str,args))
                           + "\n" + (proc.stdout + proc.stderr)[-7000:])
    return proc.stdout + proc.stderr

def lookup(name, env):
    p = subprocess.run(["kpsewhich", name], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else ""

def tex_environment(out):
    for exe in ("xelatex", "xetex", "kpsewhich"):
        if not shutil.which(exe):
            raise RuntimeError("Missing " + exe + ". Install a TeX Live distribution with XeLaTeX; see DEPENDENCIES.md.")
    env = os.environ.copy()
    # The archive owns only this vendor tree. No global TeX configuration is changed.
    # Removing !! allows TeX Live trees whose ls-R cache is missing to be searched.
    native = run(["kpsewhich", "-expand-var=$TEXMF"]).strip().replace("!!", "")
    vendor = (ROOT / "vendor/texmf").as_posix()
    env["TEXMF"] = "{" + vendor + "," + native + "}"
    cache = out / ".tex-cache"
    cache.mkdir(parents=True, exist_ok=True)
    env["TEXFORMATS"] = cache.as_posix() + "//" + os.pathsep + env.get("TEXFORMATS", "")
    required = ["ctexart.cls", "xeCJK.sty", "zhnumber.sty", "fontspec.sty",
                "mathtools.sty", "geometry.sty", "amsmath.sty",
                "FandolSong-Regular.otf", "cmr10.tfm"]
    missing = [n for n in required if not lookup(n, env)]
    if missing:
        raise RuntimeError("TeX dependencies missing: " + ", ".join(missing) + ". See DEPENDENCIES.md.")
    created_format = False
    if not lookup("xelatex.fmt", env):
        text = run(["xetex", "-ini", "-etex", "-interaction=nonstopmode",
                    "-halt-on-error", "-jobname=xelatex", "xelatex.ini"],
                   env=env, cwd=cache)
        (cache / "format_build.txt").write_text(text, encoding="utf-8")
        if not (cache / "xelatex.fmt").is_file():
            raise RuntimeError("XeLaTeX format was not generated.")
        created_format = True
    return env, created_format

def compile_tex(name, out, env):
    source = ROOT / "src" / name
    text = run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode",
                "-halt-on-error", "-file-line-error", "-recorder",
                "-output-directory=" + str(out), str(source)],
               env=env, cwd=ROOT / "src")
    log = out / (source.stem + ".log")
    output = out / (source.stem + ".pdf")
    (out / (source.stem + ".compile.txt")).write_text(text, encoding="utf-8")
    if not output.is_file():
        raise RuntimeError("No PDF produced: " + name)
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else text
    critical = [s for s in log_text.splitlines()
                if any(x in s for x in ("Overfull", "Missing character", "! LaTeX Error", "Emergency stop"))]
    if critical:
        raise RuntimeError("Layout or glyph error in " + name + "\n" + "\n".join(critical))
    warnings = [s.strip() for s in log_text.splitlines() if "Warning:" in s]
    return {"source": "src/" + name, "pdf": output.name,
            "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "warnings": warnings, "overflow_or_missing_glyph": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=("all", "pdf", "pptx", "verify"), default="all")
    p.add_argument("--out-dir", type=Path, default=Path("build"))
    args = p.parse_args()
    out = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out = out.resolve()
    if out == (ROOT / "outputs").resolve():
        raise RuntimeError("outputs/ preserves the delivered originals. Build into build/ and review before replacing.")
    out.mkdir(parents=True, exist_ok=True)
    report = {"target": args.target, "output_directory": out.name,
              "sources_modified": False, "network_required_by_build": False}
    if args.target == "verify":
        print(run([sys.executable, str(ROOT/"tools/verify_package.py")]))
        print(run([sys.executable, str(ROOT/"tools/verify_math.py")]))
        print(run([sys.executable, str(ROOT/"tools/rebuild_pptx.py"),
                   "--validate-only", str(ROOT/"outputs/简便计算_题目4页.pptx")]))
        return
    env, created_format = tex_environment(out)
    report["local_xelatex_format_created"] = created_format
    report["xelatex_version"] = run(["xelatex", "--version"]).splitlines()[0]
    report["python_version"] = sys.version.split()[0]
    report["python_packages"] = {n: importlib.metadata.version(n) for n in ("PyMuPDF", "Pillow")}
    names = SOURCES if args.target in ("all", "pdf") else [SOURCES[-1]]
    report["documents"] = []
    for name in names:
        print("Compiling " + name, flush=True)
        report["documents"].append(compile_tex(name, out, env))
    if args.target in ("all", "pdf"):
        math_out = run([sys.executable, str(ROOT/"tools/verify_math.py"),
                        "--pdf-dir", str(out), "--report", str(out/"math_validation.json")])
        report["math_validation"] = json.loads((out/"math_validation.json").read_text(encoding="utf-8"))
        print("Verified 84 questions and all solution steps.", flush=True)
    if args.target in ("all", "pptx"):
        print("Rebuilding the four-slide PPTX.", flush=True)
        run([sys.executable, str(ROOT/"tools/rebuild_pptx.py"),
             "--pdf", str(out/"简便计算_题目4页.pdf"),
             "--output", str(out/"简便计算_题目4页.pptx"),
             "--report", str(out/"pptx_validation.json")])
        report["pptx_validation"] = json.loads((out/"pptx_validation.json").read_text(encoding="utf-8"))
    report["status"] = "passed"
    (out/"build_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Build passed. New files: " + str(out), flush=True)

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

