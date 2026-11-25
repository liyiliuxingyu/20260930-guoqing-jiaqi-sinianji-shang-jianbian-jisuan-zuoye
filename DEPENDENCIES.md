# 运行环境与依赖

本次实测环境为 Linux、Python 3.12.14、XeTeX 3.141592653-2.6-0.999996（TeX Live 2025/dev/Debian），LaTeX2e 2024-11-01 patch level 2。源码保留 `ctexart` 默认字体设置，不写入另选中文或数学字体的命令。

## 必要工具

- Python 3.10 或以上。
- TeX Live 中的 `xelatex`、`xetex`、`kpsewhich` 和标准 LaTeX 宏包。所用标准宏包包括 amsmath、mathtools、geometry、fontspec、graphics 和 LaTeX3。
- 标准 Computer Modern 数学字体随 TeX 发行版提供。
- Python 依赖见 `requirements.txt`：PyMuPDF 1.26.6、Pillow 13.0.0。可在自己的虚拟环境中运行 `python -m pip install -r requirements.txt`。
- LibreOffice 只用于额外打开/渲染 PPT 验证，正常生成 PDF/PPT 不需要 Office 软件。

解释器、完整 TeX 发行版、Python 包安装文件和 Office 软件不包含在压缩包里。依赖安装完成后，构建脚本本身不联网，不需要旧对话、账号或令牌。

## 已随包保留

`vendor/texmf/` 含 ctex 2.5.10、xeCJK 3.9.1、zhnumber 3.0 的宏包及源文件，以及 Fandol 0.3 的6个常用默认字体文件和许可。保留发行方的 README、许可和源码头部；仅省略大体积说明PDF、演示文件中不需要的盲文字体。精确来源及源压缩包SHA-256在 `vendor/dependency_sources.json`。

这些兼容版宏包取自 TeX Live 2025 归档，匹配当前源文件原有编译环境。2026年的新版 ctex/xeCJK 要求较新的 LaTeX 内核，因此本包固定可实际复建的版本，没有把不兼容更新混入构建。

默认字体由 ctex 根据系统选择。在本次 Linux 验证环境中为 Fandol + Computer Modern。Windows/macOS 的 ctex 默认字体可能不同；本次没有实测那些平台。要保持原版视觉外观，使用记录中的 Linux/TeX Live 环境或人工确认平台字体后再发布。

## 构建脚本的局部恢复措施

`tools/build.py` 只调整其子进程的 TeX 搜索路径，优先查找包内 `vendor/texmf`，不会改系统配置。若系统缺少 `xelatex.fmt`，会在 `build/.tex-cache/` 内重新生成。该格式缓存与机器和引擎版本相关，不收入ZIP。

一键入口：

```bash
python tools/build.py --target all
```

可选目标为 `pdf`、`pptx`、`verify`。输出目录默认 `build/`，可用 `--out-dir` 指定其他目录；不会直接覆盖 `outputs/` 中的交付原件。

Windows可运行根目录 `build.bat`，Linux/macOS可运行 `sh build.sh`。这些包装入口沿用同一Python脚本；本次实际运行验证在Linux完成。

## 重新打包

完成有意修改并检查新输出后，手动将确认后的成品更新到 `outputs/`，同步 `checks/` 和接续说明，再执行：

```bash
python tools/package_project.py --output ../简便计算_续作工程.zip
```

打包脚本会更新SHA-256清单，并检查所有条目、压缩包CRC及解压后的校验值。请不要把旧检查记录当成新改动的验证结果。

