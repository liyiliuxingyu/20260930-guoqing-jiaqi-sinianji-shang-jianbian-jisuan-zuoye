#!/usr/bin/env python3
"""Rebuild this existing four-slide PPTX from its LaTeX-generated PDF.

The original OOXML layout is preserved. Each title/question remains a separate
picture with SVG outlines and a PNG fallback. No Office app is needed to build.
Dependencies: PyMuPDF and Pillow. Compile src/简便计算_题目4页.tex with XeLaTeX first.

Examples (run from the project root):
  python tools/rebuild_pptx.py
  python tools/rebuild_pptx.py --pdf build/简便计算_题目4页.pdf
  python tools/rebuild_pptx.py --pdf outputs/简便计算_题目4页.pdf --output build/demo.pptx

This is a recovery script added during the 2026-11-19 handoff, not a recovered
copy of the original PPTX-authoring script. It preserves the delivered design.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}
for prefix in ("p", "a", "r", "asvg"):
    ET.register_namespace(prefix, NS[prefix])


def qn(prefix: str, local: str) -> str:
    return "{" + NS[prefix] + "}" + local


def xml_bytes(root: ET.Element) -> bytes:
    # OPC readers in some Office versions expect these package roots to use
    # a default namespace rather than ElementTree's automatic ns0 prefix.
    if root.tag in (qn("pr", "Relationships"), qn("ct", "Types")):
        ET.register_namespace("", root.tag.split("}", 1)[0][1:])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_questions(path: Path) -> list[str]:
    """Read the three balanced-brace arguments of each qrow in the document."""
    text = path.read_text(encoding="utf-8")
    if r"\begin{document}" not in text:
        raise ValueError(f"Not a standalone LaTeX document: {path}")
    text = text.split(r"\begin{document}", 1)[1]
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    questions: list[str] = []
    for m in re.finditer(r"\\qrow\b", text):
        pos = m.end()
        for _ in range(3):
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos >= len(text) or text[pos] != "{":
                raise ValueError("Expected three braced arguments after \\qrow")
            start = pos + 1
            depth = 1
            pos += 1
            while pos < len(text) and depth:
                if text[pos] == "{" and text[pos - 1] != "\\":
                    depth += 1
                elif text[pos] == "}" and text[pos - 1] != "\\":
                    depth -= 1
                pos += 1
            if depth:
                raise ValueError("Unbalanced braces in LaTeX question source")
            questions.append(text[start : pos - 1].strip())
    if len(questions) != 84:
        raise ValueError(f"This layout requires 84 questions; found {len(questions)}")
    return questions


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text.replace(r"\times", "×").replace(r"\div", "÷").replace("−", "-"))


def page_lines(page: fitz.Page) -> list[dict]:
    lines = [
        line
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        if any(span["text"].strip() for span in line["spans"])
    ]
    # Current LaTeX writes one line per problem in row-major order.
    lines.sort(key=lambda line: (round(line["bbox"][1], 1), line["bbox"][0]))
    if len(lines) != 22:
        raise ValueError(f"Expected a title plus 21 single-line questions, found {len(lines)}")
    if "".join(s["text"] for s in lines[0]["spans"]).strip() != "简便计算":
        raise ValueError("Unexpected slide title; revise the template if the title changes")
    return lines


def resolve_rel(part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if part == "_rels/.rels":
        base = ""
    else:
        base = posixpath.dirname(posixpath.dirname(part))
    return posixpath.normpath(posixpath.join(base, target))


def validate_package(path: Path) -> dict:
    """Check all internal relationships plus all 88 SVG/PNG picture pairs."""
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failure: {bad}")
        names = set(archive.namelist())
        broken = []
        external = []
        for name in names:
            if not name.endswith(".rels"):
                continue
            tree = ET.fromstring(archive.read(name))
            for rel in tree:
                if rel.get("TargetMode") == "External":
                    external.append({"part": name, "target": rel.get("Target")})
                elif resolve_rel(name, rel.get("Target", "")) not in names:
                    broken.append({"part": name, "target": rel.get("Target")})
        if broken:
            raise ValueError(f"Broken internal relationships: {broken}")
        if external:
            raise ValueError("This offline deck must not depend on external relationships")

        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        slide_ids = presentation.findall("p:sldIdLst/p:sldId", NS)
        if len(slide_ids) != 4:
            raise ValueError(f"Expected 4 slides, found {len(slide_ids)}")
        sz = presentation.find("p:sldSz", NS)
        width, height = int(sz.get("cx")), int(sz.get("cy"))
        if abs(width / height - 16 / 9) > 1e-6:
            raise ValueError("Slide size is not 16:9")

        slides = []
        for i in range(1, 5):
            part = f"ppt/slides/slide{i}.xml"
            tree = ET.fromstring(archive.read(part))
            pics = tree.findall("p:cSld/p:spTree/p:pic", NS)
            if len(pics) != 22:
                raise ValueError(f"Slide {i} has {len(pics)} pictures instead of 22")
            relpart = f"ppt/slides/_rels/slide{i}.xml.rels"
            rels = {r.get("Id"): r for r in ET.fromstring(archive.read(relpart))}
            for pic in pics:
                png = pic.find("p:blipFill/a:blip", NS)
                svg = pic.find(".//asvg:svgBlip", NS)
                if png is None or svg is None:
                    raise ValueError(f"Slide {i} has a picture without SVG/PNG fallbacks")
                for elem, suffix in ((png, ".png"), (svg, ".svg")):
                    rid = elem.get(qn("r", "embed"))
                    target = resolve_rel(relpart, rels[rid].get("Target"))
                    if not target.endswith(suffix):
                        raise ValueError(f"Incorrect media type: {target}")
                    payload = archive.read(target)
                    if suffix == ".svg":
                        svg_root = ET.fromstring(payload)
                        if any(n.tag.rsplit("}", 1)[-1] == "text" for n in svg_root.iter()):
                            raise ValueError("SVG must contain outlines, not font-dependent text")
                    else:
                        with Image.open(io.BytesIO(payload)) as image:
                            image.verify()
                xfrm = pic.find("p:spPr/a:xfrm", NS)
                off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
                x, y = int(off.get("x")), int(off.get("y"))
                cx, cy = int(ext.get("cx")), int(ext.get("cy"))
                if min(x, y, cx, cy) < 0 or x + cx > width or y + cy > height:
                    raise ValueError(f"Picture extends outside slide {i}")
            slides.append({"slide": i, "pictures": 22, "questions": 21, "svg_png_pairs": 22})
        return {
            "slide_count": 4,
            "questions": 84,
            "slide_size_emu": [width, height],
            "internal_relationships_valid": True,
            "external_relationships": 0,
            "svg_text_converted_to_paths": True,
            "slides": slides,
        }


def rebuild(pdf_path: Path, source_path: Path, output: Path, scale: float) -> dict:
    template = ROOT / "assets/pptx_template"
    if not template.is_dir():
        raise FileNotFoundError(f"Missing template: {template}")
    parts = {p.relative_to(template).as_posix(): p.read_bytes() for p in template.rglob("*") if p.is_file()}
    questions = parse_questions(source_path)
    doc = fitz.open(pdf_path)
    if len(doc) != 4:
        raise ValueError(f"Expected 4 PDF pages, found {len(doc)}")
    sizes = {tuple(round(x, 3) for x in p.rect[2:]) for p in doc}
    if sizes != {(960.0, 540.0)}:
        raise ValueError(f"Expected a 960 by 540 point PDF, found {sizes}")

    for page_no, page in enumerate(doc, 1):
        lines = page_lines(page)
        local_questions = questions[(page_no - 1) * 21 : page_no * 21]
        for q, line in zip(local_questions, lines[1:]):
            actual = "".join(s["text"] for s in line["spans"])
            if normalized(q) != normalized(actual):
                raise ValueError(f"PDF/source mismatch on page {page_no}: {q!r} versus {actual!r}. Compile the source again.")
        part = f"ppt/slides/slide{page_no}.xml"
        slide = ET.fromstring(parts[part])
        pics = slide.findall("p:cSld/p:spTree/p:pic", NS)
        if len(pics) != 22:
            raise ValueError("Template object count changed")
        relpart = f"ppt/slides/_rels/slide{page_no}.xml.rels"
        relroot = ET.fromstring(parts[relpart])
        rels = {r.get("Id"): r for r in relroot}

        for item, (line, pic) in enumerate(zip(lines, pics)):
            rect = fitz.Rect(line["bbox"]) + (-2, -2, 2, 2)
            if not page.rect.contains(rect):
                raise ValueError(f"Clipped question or title on PDF page {page_no}")
            media_base = f"latex_page{page_no:02d}_item{item:02d}"
            png_name, svg_name = f"ppt/media/{media_base}.png", f"ppt/media/{media_base}.svg"
            crop = fitz.open()
            crop_page = crop.new_page(width=rect.width, height=rect.height)
            crop_page.show_pdf_page(crop_page.rect, doc, page_no - 1, clip=rect)
            parts[svg_name] = crop_page.get_svg_image(text_as_path=True).encode("utf-8")
            parts[png_name] = crop_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
            crop.close()

            png = pic.find("p:blipFill/a:blip", NS)
            svg = pic.find(".//asvg:svgBlip", NS)
            rels[png.get(qn("r", "embed"))].set("Target", "../media/" + media_base + ".png")
            rels[svg.get(qn("r", "embed"))].set("Target", "../media/" + media_base + ".svg")
            xfrm = pic.find("p:spPr/a:xfrm", NS)
            off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
            for key, value in (("x", rect.x0), ("y", rect.y0)):
                off.set(key, str(round(value * 12700)))
            for key, value in (("cx", rect.width), ("cy", rect.height)):
                ext.set(key, str(round(value * 12700)))
            nv = pic.find("p:nvPicPr/p:cNvPr", NS)
            nv.set("descr", "简便计算" if item == 0 else "LaTeX: " + local_questions[item - 1])
        parts[part] = xml_bytes(slide)
        parts[relpart] = xml_bytes(relroot)

        # Retain up-to-date question source in speaker notes for easy recovery.
        notes_part = f"ppt/notesSlides/notesSlide{page_no}.xml"
        notes = ET.fromstring(parts[notes_part])
        for shape in notes.findall("p:cSld/p:spTree/p:sp", NS):
            ph = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
            if ph is None or ph.get("type") != "body":
                continue
            body = shape.find("p:txBody", NS)
            for paragraph in body.findall("a:p", NS):
                body.remove(paragraph)
            for text in ["LaTeX题目源码（本页仅展示题目）：", *local_questions]:
                paragraph = ET.SubElement(body, qn("a", "p"))
                run = ET.SubElement(paragraph, qn("a", "r"))
                ET.SubElement(run, qn("a", "t")).text = text
        parts[notes_part] = xml_bytes(notes)

    types = ET.fromstring(parts["[Content_Types].xml"])
    for elem in list(types):
        if elem.get("PartName", "").startswith("/ppt/media/"):
            types.remove(elem)
    known_extensions = {e.get("Extension") for e in types}
    for ext, mime in (("svg", "image/svg+xml"), ("png", "image/png")):
        if ext not in known_extensions:
            ET.SubElement(types, qn("ct", "Default"), {"Extension": ext, "ContentType": mime})
    parts["[Content_Types].xml"] = xml_bytes(types)
    # Update thumbnail without changing any slide text or layout.
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    thumbnail = io.BytesIO()
    image.save(thumbnail, "JPEG", quality=90)
    parts["docProps/thumbnail.jpeg"] = thumbnail.getvalue()
    doc.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(parts):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, parts[name])
    report = validate_package(temporary)
    temporary.replace(output)
    report.update({
        "input_pdf": str(pdf_path),
        "input_tex": str(source_path),
        "output_pptx": str(output),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "png_pixels_per_pdf_point": scale,
        "editability": "Each title/question is a separate SVG/PNG picture. Change expression text in the LaTeX source and rebuild.",
        "notes_source_updated": True,
    })
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", type=Path, default=ROOT / "build/简便计算_题目4页.pdf")
    parser.add_argument("--source", type=Path, default=ROOT / "src/简便计算_题目4页.tex")
    parser.add_argument("--output", type=Path, default=ROOT / "build/简便计算_题目4页.pptx")
    parser.add_argument("--report", type=Path, help="Optional JSON validation report")
    parser.add_argument("--png-scale", type=float, default=4.0, help="PNG pixels per PDF point (default 4 = 288 dpi)")
    parser.add_argument("--validate-only", type=Path, metavar="PPTX", help="Check an existing PPTX without rebuilding")
    args = parser.parse_args()
    if args.png_scale < 2:
        parser.error("--png-scale must be at least 2")
    report = validate_package(args.validate_only) if args.validate_only else rebuild(args.pdf, args.source, args.output, args.png_scale)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
