#!/usr/bin/env python3
"""Validate the delivered 84-question project without modifying its sources.

Usage (from any working directory):
    python tools/verify_math.py
    python tools/verify_math.py --pdf-dir build
    python tools/verify_math.py --report checks/math_validation.json --write-data

Source arithmetic uses only the Python standard library. PDF inspection requires
PyMuPDF. No Python eval(), OCR service, network connection or old chat state is used.
The image transcription baseline below was visually reviewed on 2026-11-19.
After an intentional change to the questions, review/update that baseline or use
--skip-original-baseline; the latter is explicitly reported as an unchecked item.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path


SOURCE_NAMES = {
    "questions": "简便计算_A4_题目.tex",
    "answers": "简便计算_A4答案_新版.tex",
    "combined": "简便计算_A4合订本_新版.tex",
    "slides": "简便计算_题目4页.tex",
}

# Order is the delivered page order, i.e. original worksheets 二、三、四、五.
# Strings were checked against the image pixels, including close-up inspection
# of page 2 question 18 and page 4 question 9.
IMAGE_TRANSCRIPTIONS = [
    {
        "file": "1000072212.jpg",
        "sha256": "98751c72ba1248bfeb4ebef9e7d60b7da9f33d3ea196d567102cfefd79a9582b",
        "questions": [
            "608-491", "730/5/2", "212-97",
            "25*(4*54)", "4*61*5", "125*(8*39)",
            "9*125*8*3", "216-96", "5*93*4",
            "5*51*4", "209-95", "55*25*8",
            "125*11*8", "320-208", "5*69*4",
            "89000/125/8", "125*(8*92)", "9*4*25*5",
            "500/5/4", "320/10/2", "2100/25/4",
        ],
    },
    {
        "file": "1000072211.jpg",
        "sha256": "b27d6670f9202eb976d3fce78a972bd2233ac1d2df4fac9ee2dd47885a7976c1",
        "questions": [
            "1920/4/5", "296-207", "56*125",
            "760/2/10", "163-103", "1420/10/2",
            "125*79*8", "57*8*125", "18000/8/125",
            "9*125*8*3", "54000/8/125", "125*27*8",
            "5*53*4", "5*79*4", "15*25*8",
            "13*125*4", "509-408", "25*89*4",
            "125*12", "4*77*25", "172-94",
        ],
    },
    {
        "file": "1000072209.jpg",
        "sha256": "455b3e16f96c7c1a1b4489a8fd4befbf7fc3b3259303a386635ad221f3175907",
        "questions": [
            "4*39*25", "900/2/5", "9100/4/25",
            "8*(125*19)", "19000/8/125", "299-108",
            "47*8*125", "484-392", "5*49*4",
            "399-296", "93000/8/125", "25*72",
            "13*125*8", "230/5/2", "167-91",
            "190-109", "9*8*125*6", "7*25*4*5",
            "508-399", "25*79*4", "5*19*4",
        ],
    },
    {
        "file": "1000072210.jpg",
        "sha256": "83c9cf7d41691ae4c0414a20fa5854413f7c8b50ec5211ef6fae1148337a439e",
        "questions": [
            "420/5/2", "125*63*8", "387-192",
            "64*125", "810/2/5", "5*25*4*6",
            "88*25", "250/5/2", "2*49*5",
            "9300/4/25", "159-104", "288-193",
            "9*25*4*3", "478-407", "16*125",
            "7*125*4*8", "4*67*5", "25*79*4",
            "603-505", "330/2/5", "8*51*125",
        ],
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(expression: str) -> str:
    """Canonicalize only notation and whitespace, not arithmetic structure."""
    for before, after in [
        (r"\times", "*"), (r"\div", "/"), ("×", "*"), ("÷", "/"),
        ("−", "-"), ("–", "-"), (r"\(", ""), (r"\)", ""),
    ]:
        expression = expression.replace(before, after)
    return re.sub(r"\s+", "", expression)


def exact_value(expression: str) -> Fraction:
    node = ast.parse(normal(expression), mode="eval")

    def visit(n: ast.AST) -> Fraction:
        if isinstance(n, ast.Expression):
            return visit(n.body)
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return Fraction(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            result = visit(n.operand)
            return result if isinstance(n.op, ast.UAdd) else -result
        if isinstance(n, ast.BinOp):
            left, right = visit(n.left), visit(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                return left / right
        raise ValueError(f"不支持的算式节点: {ast.dump(n)}")

    return visit(node)


def body(source: str) -> str:
    return source.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0]


def code_without_comments(source: str) -> str:
    return "\n".join(line.split("%", 1)[0] for line in source.splitlines())


def parse_questions(source: str) -> list[str]:
    rows = re.findall(
        r"\\qrow\s*\n\{([^{}\n]+)\}\s*\n\{([^{}\n]+)\}\s*\n\{([^{}\n]+)\}",
        body(source),
    )
    return [normal(expression) for row in rows for expression in row]


def parse_answers(source: str) -> list[list[str]]:
    solutions = []
    blocks = re.findall(r"\{\\solution\{\s*(.*?)\n\}\}", body(source), re.S)
    for block in blocks:
        parts = [part.strip() for part in block.split(r"\\") if part.strip()]
        first = re.fullmatch(r"&\s*\\problemline\{(.*)\}", parts[0], re.S)
        if first is None:
            raise ValueError(f"无法解析首行: {parts[0]}")
        result = [first.group(1).strip()]
        for part in parts[1:]:
            following = re.fullmatch(r"=\s*&\s*(.*)", part, re.S)
            if following is None:
                raise ValueError(f"无法解析等式行: {part}")
            result.append(following.group(1).strip())
        solutions.append(result)
    return solutions


def pdf_lines(page):
    result = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            chars = [c for span in line["spans"] for c in span["chars"] if c["c"].strip()]
            if chars:
                result.append(("".join(c["c"] for c in chars), chars))
    return result


def inspect_answer_pdf(document, solutions: list[list[str]], check, report):
    max_start_delta = 0.0
    max_equal_delta = 0.0
    parentheses_rows = 0
    checked_groups = 0
    for pidx, page in enumerate(document):
        groups = []
        for text, chars in pdf_lines(page):
            if text.startswith("简便计算"):
                continue
            if text.startswith("="):
                if not groups:
                    check(False, f"答案PDF第{pidx + 1}页出现无原题的等号")
                    continue
                groups[-1].append((text, chars))
            elif text[0].isdigit():
                groups.append([(text, chars)])
            else:
                check(False, f"答案PDF出现非预期文字: {text}")
        check(len(groups) == 21, f"答案PDF第{pidx + 1}页21题")
        for qidx, group in enumerate(groups):
            absolute = pidx * 21 + qidx
            if absolute >= len(solutions):
                continue
            expected = solutions[absolute]
            actual = [normal(text.removeprefix("=")) for text, _ in group]
            check(actual == [normal(x) for x in expected], f"答案PDF第{pidx + 1}页第{qidx + 1}题与源码一致")
            if len(group) < 2:
                continue
            x_start = group[0][1][0]["origin"][0]
            x_equal = group[1][1][0]["origin"][0]
            for text, chars in group[1:]:
                if len(chars) < 2:
                    check(False, f"答案PDF第{pidx + 1}页第{qidx + 1}题存在空等式行")
                    continue
                start_delta = abs(chars[1]["origin"][0] - x_start)
                equal_delta = abs(chars[0]["origin"][0] - x_equal)
                max_start_delta = max(max_start_delta, start_delta)
                max_equal_delta = max(max_equal_delta, equal_delta)
                check(start_delta < 0.08, f"答案PDF第{pidx + 1}页第{qidx + 1}题完整算式左端对齐")
                check(equal_delta < 0.08, f"答案PDF第{pidx + 1}页第{qidx + 1}题等号竖直对齐")
                check(chars[0]["bbox"][2] < chars[1]["bbox"][0], f"答案PDF第{pidx + 1}页第{qidx + 1}题等号列与算式分开")
                if chars[1]["c"] == "(":
                    parentheses_rows += 1
                    check(len(chars) > 2 and chars[2]["origin"][0] > chars[1]["origin"][0], f"答案PDF第{pidx + 1}页第{qidx + 1}题左括号正常占位")
            checked_groups += 1
    report["pdf_alignment"] = {
        "solutions_checked": checked_groups,
        "max_expression_start_deviation_pt": round(max_start_delta, 6),
        "max_equals_start_deviation_pt": round(max_equal_delta, 6),
        "normal_leading_parenthesis_rows": parentheses_rows,
        "tolerance_pt": 0.08,
        "measurement": "PDF字符origin；原题与完整算式首字符左端；字形墨迹轮廓不是该检查的基准",
    }


def run(args) -> dict:
    root = args.root.resolve()
    failures = []
    passed = 0

    def check(condition: bool, label: str):
        nonlocal passed
        if condition:
            passed += 1
        else:
            failures.append(label)

    sources = {key: (root / "src" / name).read_text(encoding="utf-8") for key, name in SOURCE_NAMES.items()}
    questions = parse_questions(sources["questions"])
    slide_questions = parse_questions(sources["slides"])
    combined_questions = parse_questions(sources["combined"])
    solutions = parse_answers(sources["answers"])
    combined_solutions = parse_answers(sources["combined"])
    report = {
        "schema_version": 1,
        "status": "running",
        "question_count": len(questions),
        "source_files_sha256": {name: sha256(root / "src" / name) for name in SOURCE_NAMES.values()},
        "manual_image_review": {
            "review_date": "2026-11-19",
            "method": "逐页直接看图并对不清晰字符放大核对；自动脚本使用其固定转录基准与图像SHA-256",
            "sources": [{"delivered_page": i + 1, "file": x["file"], "sha256": x["sha256"]} for i, x in enumerate(IMAGE_TRANSCRIPTIONS)],
            "note": "原图1000072209.jpg的第11题已经是93000÷8÷125；早期对话称原题为9300，与现存原图不符。现行93000与原图及后续用户指令一致。",
            "rerun_does_not_repeat_visual_review": True,
        },
        "not_checked": [],
    }
    for name, items in [("题目", questions), ("PPT题目", slide_questions), ("合订本题目", combined_questions), ("答案", solutions), ("合订本答案", combined_solutions)]:
        check(len(items) == 84, f"{name}总数84")
    check(questions == slide_questions == combined_questions, "题目/PPT/合订本题目顺序相同")
    check(questions == [normal(s[0]) for s in solutions], "题目与答案原题逐题相同")
    check(solutions == combined_solutions, "独立答案与合订本脱式过程逐行相同")
    for key, expected_pages in [("questions", 4), ("answers", 4), ("slides", 4), ("combined", 8)]:
        check(len(body(sources[key]).split(r"\newpage")) == expected_pages, f"{key}源码显式分页数{expected_pages}")

    if args.skip_original_baseline:
        report["not_checked"].append("按命令行要求跳过原图固定转录基准与原图哈希检查")
    else:
        image_questions = [q for record in IMAGE_TRANSCRIPTIONS for q in record["questions"]]
        check(questions == image_questions, "84题与人工逐页图像转录基准完全一致")
        for record in IMAGE_TRANSCRIPTIONS:
            path = root / "originals" / record["file"]
            check(path.is_file() and sha256(path) == record["sha256"], f"原图未改变:{record['file']}")

    if len(questions) == 84:
        check(questions[52] == "93000/8/125", "第3页第11题保持93000÷8÷125")
        check(questions[72] == "9300/4/25", "第4页第10题保持9300÷4÷25")
    equalities = 0
    for i, solution in enumerate(solutions):
        check(len(solution) >= 4, f"第{i + 1}题至少三步等式")
        value = exact_value(solution[0])
        for step in solution[1:]:
            check(exact_value(step) == value, f"第{i + 1}题等式保持精确数值:{step}")
            equalities += 1
        check(value.denominator == 1, f"第{i + 1}题最终结果为整数")
        check(re.fullmatch(r"\d+", solution[-1]) is not None, f"第{i + 1}题已算到最终数值")
    report["equality_steps_checked"] = equalities
    report["duplicate_expressions_preserved"] = {q: count for q, count in Counter(questions).items() if count > 1}
    for key in ["answers", "combined"]:
        code = code_without_comments(sources[key])
        check(r"\leadingparen" not in code and r"\mathllap" not in code, f"{key}不使用悬挂左括号")
        check(re.search(r"\\hspace\*?\s*\{\s*-", code) is None, f"{key}无题目负水平位移")
        check(r"\newcommand{\problemline}[1]{#1}" in code, f"{key}首行不额外位移")
        check(r"{ctexart}" in code, f"{key}使用ctexart")
        check(all(x not in code for x in [r"\setmainfont", r"\setCJKmainfont", r"\setmathfont", "fontset="]), f"{key}未手动替换默认字体")

    data = {
        "schema_version": 1,
        "source": "src/简便计算_A4答案_新版.tex",
        "source_sha256": report["source_files_sha256"][SOURCE_NAMES["answers"]],
        "order": "每页7行3列，按行从左到右；4页共84题；重复题保留",
        "problems": [
            {
                "id": i + 1,
                "page": i // 21 + 1,
                "within_page": i % 21 + 1,
                "row": (i % 21) // 3 + 1,
                "column": i % 3 + 1,
                "question_latex": s[0],
                "steps_latex": s[1:],
                "question_ascii": normal(s[0]),
                "answer": int(exact_value(s[0])),
                "original_image": IMAGE_TRANSCRIPTIONS[i // 21]["file"],
            }
            for i, s in enumerate(solutions)
        ],
    }

    if args.sources_only:
        report["not_checked"].append("按命令行要求跳过PDF页数、尺寸、文本、坐标检查")
    else:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PDF核验需要PyMuPDF；安装依赖或使用--sources-only并保留该限制说明") from exc
        pdf_root = args.pdf_dir if args.pdf_dir.is_absolute() else root / args.pdf_dir
        documents = {key: fitz.open(pdf_root / Path(name).with_suffix(".pdf")) for key, name in SOURCE_NAMES.items()}
        try:
            for key, expected in [("questions", 4), ("answers", 4), ("combined", 8), ("slides", 4)]:
                doc = documents[key]
                check(len(doc) == expected, f"{key}PDF页数{expected}")
                for pidx, page in enumerate(doc):
                    if key == "slides":
                        check(abs(page.rect.width / page.rect.height - 16 / 9) < 0.001, f"幻灯片PDF第{pidx + 1}页16:9")
                    else:
                        check(abs(page.rect.width - 595.276) < 0.1 and abs(page.rect.height - 841.890) < 0.1, f"{key}PDF第{pidx + 1}页A4纵向")
                    for text, chars in pdf_lines(page):
                        check(all(c["bbox"][0] >= 0 and c["bbox"][1] >= 0 and c["bbox"][2] <= page.rect.width + 0.1 and c["bbox"][3] <= page.rect.height + 0.1 for c in chars), f"{key}PDF第{pidx + 1}页文字位于页面内:{text[:24]}")
            for key in ["questions", "slides"]:
                for pidx, page in enumerate(documents[key]):
                    actual = [normal(text) for text, _ in pdf_lines(page) if not text.startswith("简便计算")]
                    check(actual == questions[pidx * 21:(pidx + 1) * 21], f"{key}PDF第{pidx + 1}页21题内容顺序与源码一致")
            inspect_answer_pdf(documents["answers"], solutions, check, report)
            if len(documents["combined"]) == 8:
                for i in range(4):
                    check(normal(documents["combined"][i].get_text()) == normal(documents["questions"][i].get_text()), f"合订本第{i + 1}页与题目版一致")
                    check(normal(documents["combined"][i + 4].get_text()) == normal(documents["answers"][i].get_text()), f"合订本第{i + 5}页与答案版一致")
            report["pdf_files_sha256"] = {name.replace(".tex", ".pdf"): sha256(pdf_root / Path(name).with_suffix(".pdf")) for name in SOURCE_NAMES.values()}
        finally:
            for doc in documents.values():
                doc.close()

    report["checks_passed"] = passed
    report["failures"] = failures
    report["status"] = "passed" if not failures else "failed"
    report["scope_limit"] = "验证题目一致性、等式精确数值、PDF文本和几何排版；不把自动检查解释为所有教学解法都唯一或最优。PPTX本体由单独检查脚本处理。"
    if args.write_data:
        check(not failures, "仅在验证通过时导出结构化题库")
        if not failures:
            destination = root / "data" / "problems.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--write-data", action="store_true")
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--skip-original-baseline", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args)
    except Exception as exc:
        report = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    if args.report:
        target = args.report if args.report.is_absolute() else args.root / args.report
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
