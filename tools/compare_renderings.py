#!/usr/bin/env python3
"""Compare rebuilt PDFs with preserved delivery PDFs using one renderer."""
from pathlib import Path
import argparse, json, sys
import fitz

ROOT=Path(__file__).resolve().parents[1]
NAMES=["简便计算_A4_题目.pdf","简便计算_A4答案_新版.pdf",
       "简便计算_A4合订本_新版.pdf","简便计算_题目4页.pdf"]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--generated-dir",type=Path,default=ROOT/"build")
    p.add_argument("--reference-dir",type=Path,default=ROOT/"outputs")
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    report={"renderer": "PyMuPDF "+fitz.VersionBind,"dpi":144,"documents":[]}
    equal=True
    for name in NAMES:
        with fitz.open(a.reference_dir/name) as ref, fitz.open(a.generated_dir/name) as new:
            item={"file":name,"reference_pages":len(ref),"new_pages":len(new),"pages":[]}
            if len(ref)!=len(new):equal=False
            for i in range(min(len(ref),len(new))):
                px=ref[i].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                py=new[i].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                text_equal="".join(ref[i].get_text().split())=="".join(new[i].get_text().split())
                pixel_equal=px.width==py.width and px.height==py.height and px.samples==py.samples
                item["pages"].append({"page":i+1,"text_equal":text_equal,"pixels_identical":pixel_equal,
                                      "dimensions_equal":ref[i].rect==new[i].rect})
                equal=equal and text_equal and pixel_equal
            report["documents"].append(item)
    report["all_pages_text_and_pixels_identical"]=equal
    result=json.dumps(report,ensure_ascii=False,indent=2)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(result+"\n",encoding="utf-8")
    print(result)
    return 0 if equal else 1

if __name__=="__main__":sys.exit(main())

