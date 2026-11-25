# 20260930国庆假期四年级上简便计算作业

四年级上册简便计算作业，共 **84题**。本仓库收录可打印的A4练习卷、完整脱式答案、题目答案合订本、四页纯题目PPT，以及可继续修改和重建的LaTeX工程。

## 直接查看与下载

| 文件 | 用途 |
| --- | --- |
| [A4题目PDF](outputs/简便计算_A4_题目.pdf) | 4页，只有题目，留有计算空间 |
| [A4完整答案PDF](outputs/简便计算_A4答案_新版.pdf) | 4页，保留脱式计算过程和最终对齐方式 |
| [A4题目答案合订本PDF](outputs/简便计算_A4合订本_新版.pdf) | 8页，前4页题目、后4页答案 |
| [四页题目PPT](outputs/简便计算_题目4页.pptx) | 16:9课件，每页21题 |
| [四页课件PDF](outputs/简便计算_题目4页.pdf) | 便于直接预览课件 |
| [LaTeX源码目录](src/) | 4份现行可编辑源码 |

下载全部工程：在仓库页面选择 **Code → Download ZIP**，或使用Git克隆。本仓库保留工程文件的目录结构，可逐个查看。

```bash
git clone https://github.com/liyiliuxingyu/20260930-guoqing-jiaqi-sinianji-shang-jianbian-jisuan-zuoye.git
cd 20260930-guoqing-jiaqi-sinianji-shang-jianbian-jisuan-zuoye
```

## 在新对话中继续

提供本仓库链接或下载的ZIP，并说明：

> 请先阅读00_接续说明.txt、README.md和AGENTS.md，运行工程校验，再从src中的现行LaTeX源码继续。保留84题的原顺序和最后确认的答案对齐方式。

公开整理记录见 [PUBLICATION.md](PUBLICATION.md)。完整中文标题保留在首页和仓库说明中；GitHub仓库地址使用对应拼音名称。

## 工程说明

本工程用于将84题练习卷、完整答案和四页课件带到新对话继续修改。先读 [00_接续说明.txt](00_接续说明.txt)，再按下列步骤运行。工程整理日期：2026-11-19；公开仓库整理日期：2026-11-25。

## 现行源码与成品

| 用途 | `src/` 中的源文件 | `outputs/` 中的原交付成品 |
| --- | --- | --- |
| A4纯题目，4页 | `简便计算_A4_题目.tex` | `简便计算_A4_题目.pdf` |
| A4完整答案，4页 | `简便计算_A4答案_新版.tex` | `简便计算_A4答案_新版.pdf` |
| A4题目答案合订本，8页 | `简便计算_A4合订本_新版.tex` | `简便计算_A4合订本_新版.pdf` |
| 16:9纯题目课件，4页 | `简便计算_题目4页.tex` | `简便计算_题目4页.pdf`、`简便计算_题目4页.pptx` |

只将这四份 `.tex` 作为默认编辑入口。它们是独立文档；改动题目时须同步相关文档。`data/problems.json` 用于核对题目和计算过程，不是自动生成四份源码的入口。

## 环境与构建

需要 Python 3、XeLaTeX，以及可提供文档所用标准宏包的 TeX 发行版。推荐使用具备中文支持的 TeX Live 或等效环境。Python 依赖为 PyMuPDF、Pillow，版本记录见 `requirements.txt`。首次准备依赖后，正常构建不需要调用旧对话或在线服务。

包内 `vendor/texmf/` 保留用于恢复构建的 ctex、xeCJK、zhnumber 兼容版及 Fandol 字体、源文件和许可。TeX 引擎、其他标准宏包、Python 解释器及 Office 软件不包含在包内。依赖来源见 `vendor/dependency_sources.json`。

在解压后的工程根目录执行：

```bash
python -m pip install -r requirements.txt
python tools/verify_package.py
python tools/verify_math.py
python tools/build.py --target all
python tools/verify_math.py --pdf-dir build
```

构建文件写到 `build/`，保留 `outputs/` 中原交付版本。纯数学校验使用精确有理数，检查84题及258步等式；它不声称每种解法都是唯一或最短的。

## 修改和重建 PPT

在 `src/简便计算_题目4页.tex` 修改公式，再运行完整构建。每道题会成为可独立移动、缩放的SVG图形，并带PNG后备图像；它不是PowerPoint中可逐字输入的原生公式框。

也可直接使用已交付的幻灯片PDF验证重建：

```bash
python tools/rebuild_pptx.py --pdf outputs/简便计算_题目4页.pdf
```

`tools/rebuild_pptx.py` 为本次补写；原生成程序未找回。它结合 `assets/pptx_template/` 和 `assets/pptx_layout.json` 恢复当前四页、每页7行3列的布局。若改变页数、题数或改成多行公式，须一并调整模板和脚本。

## 有意改题后如何继续

仅调整字号、间距或版式时，保留原图基准校验。若用户明确要求修改题目数值，应同步四份源码，再同步维护 `tools/verify_math.py` 的 `IMAGE_TRANSCRIPTIONS`、两道指定位置的保护检查及相关说明，并用 `--write-data` 更新 `data/problems.json`。这些变更必须记录新的依据，不能把新题仍标成与旧扫描图一致。`--skip-original-baseline` 只跳过原图对照，仍会检查两道已明确指定的题目。

重新打包前，必需文件清单 `REQUIRED_FILES.json` 会先检查源码、成品、工具、模板、字体和原图是否存在，避免误删文件后被新的哈希清单掩盖。只有用户要求调整工程结构时才更新这一清单。

## 目录用途

| 路径 | 内容 |
| --- | --- |
| `src/`、`outputs/` | 现行源码、已交付成品 |
| `originals/` | 4张原题图和1张最终对齐参考照片 |
| `assets/` | PPT模板、对象位置及2张现行预览 |
| `tools/`、`data/` | 构建与校验工具、题库核对数据 |
| `checks/` | 本次实际完成的核验记录 |
| `vendor/` | 兼容依赖、字体、来源及许可 |
| `history/` | 已找回的旧版和全部来源状态清单 |
| `build/` | 运行时生成，可重新构建 |

原图与现行页序：第1页对应 `1000072212.jpg`；第2页对应 `1000072211.jpg`；第3页对应 `1000072209.jpg`；第4页对应 `1000072210.jpg`。

## 验证结果与限制

- 84道题已逐图复核，四份现行源码及PDF内容一致；全部258步等式通过精确计算。答案等号独立对齐，38行开头的左括号正常占位。
- 现有PDF输入重建的PPT通过结构、内部引用、页数及对象边界检查。LibreOffice成功打开原版和重建版；同一渲染器下4页对应图像逐像素一致。
- 完整干净解压、源码编译及重建验证：已通过。ZIP解压到另一目录后，不使用旧build缓存，完成4份源码的XeLaTeX编译及4页PPT重建；4份PDF共20页在144dpi下与交付原件逐页像素一致。详见 checks/clean_extract_build.json 和 checks/pdf_render_comparison.json。
- 尚未在Microsoft PowerPoint或WPS桌面界面验证。不承诺不同TeX、PyMuPDF和Office版本产生字节完全相同的文件。
- 现行11份文件、5张原图/参考图和3份旧A3文件已恢复；另27条早期文件引用无法读取，详见 `history/source_inventory.json`。未声称所有旧版都已恢复。

本包保存的是文件与继续工作的依据，不是运行中会话或完整虚拟机快照。新对话上传ZIP后，按入口说明继续即可。
