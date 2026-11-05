#!/usr/bin/env python3
"""Convert CivicOS markdown docs to styled PDF files.

Usage:
    python scripts/generate_pdf.py
    python scripts/generate_pdf.py --input docs/TRD-CIVICOS-001.md
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import zlib
from pathlib import Path

import markdown
import requests
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
OUTPUT_DIR = DOCS_DIR / "pdf"

CSS = """
@page {
    size: A4;
    margin: 2cm 2.2cm 2.5cm 2.2cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        bottom: 1cm;
        margin-left: 2.2cm;
        margin-right: 2.2cm;
        height: 1cm;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #1a1a2e;
}
h1 {
    font-size: 22pt;
    color: #0f3460;
    border-bottom: 2px solid #0f3460;
    padding-bottom: 6px;
    margin-top: 0;
}
h2 {
    font-size: 15pt;
    color: #16213e;
    margin-top: 22px;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 4px;
}
h3 {
    font-size: 12pt;
    color: #1a1a2e;
    margin-top: 16px;
}
h4 { font-size: 11pt; color: #333; }
p { margin: 6px 0; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9pt;
}
th {
    background-color: #0f3460;
    color: white;
    padding: 6px 8px;
    text-align: left;
}
td {
    border: 1px solid #ccc;
    padding: 5px 8px;
    vertical-align: top;
}
tr:nth-child(even) td { background-color: #f5f7fa; }
code, pre {
    font-family: Courier, monospace;
    font-size: 8pt;
    background-color: #f0f4f8;
}
pre {
    padding: 10px;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.3;
}
code { padding: 1px 4px; }
blockquote {
    border-left: 3px solid #0f3460;
    margin: 10px 0;
    padding: 4px 12px;
    color: #555;
    background: #f8f9fb;
}
hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
ul, ol { margin: 6px 0; padding-left: 22px; }
li { margin: 3px 0; }
.diagram {
    text-align: center;
    margin: 16px 0;
    page-break-inside: avoid;
}
.diagram img { max-width: 100%; }
.diagram-caption {
    font-size: 8pt;
    color: #666;
    font-style: italic;
    margin-top: 4px;
}
.cover-title {
    font-size: 28pt;
    color: #0f3460;
    margin-top: 80px;
}
.cover-meta {
    font-size: 11pt;
    color: #555;
    margin-top: 30px;
}
.footer-text {
    font-size: 8pt;
    color: #888;
    text-align: center;
}
"""


def encode_kroki(diagram: str) -> str:
    compressed = zlib.compress(diagram.encode("utf-8"), 9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def render_mermaid(diagram: str, caption: str = "Architecture Diagram") -> str:
    try:
        encoded = encode_kroki(diagram.strip())
        url = f"https://kroki.io/mermaid/png/{encoded}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode("ascii")
        return (
            f'<div class="diagram">'
            f'<img src="data:image/png;base64,{b64}" alt="{caption}"/>'
            f'<div class="diagram-caption">{caption}</div>'
            f"</div>"
        )
    except Exception as exc:
        return (
            f"<pre><strong>[Diagram: {caption}]</strong>\n"
            f"(Mermaid source — render unavailable: {exc})\n\n"
            f"{diagram.strip()}</pre>"
        )


def preprocess_mermaid(md_text: str) -> str:
    pattern = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
    counter = [0]

    def replacer(match: re.Match[str]) -> str:
        counter[0] += 1
        diagram = match.group(1)
        caption = f"Figure {counter[0]}: Architecture Diagram"
        return render_mermaid(diagram, caption)

    return pattern.sub(replacer, md_text)


def build_html(md_text: str, title: str) -> str:
    md_text = preprocess_mermaid(md_text)
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
    <div id="footerContent">
        <div class="footer-text">{title} — CivicOS Institute — Confidential Draft</div>
    </div>
    {body}
</body>
</html>"""


def md_to_pdf(input_path: Path, output_path: Path) -> None:
    md_text = input_path.read_text(encoding="utf-8")
    title = input_path.stem.replace("-", " ")
    html = build_html(md_text, title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as pdf_file:
        status = pisa.CreatePDF(html, dest=pdf_file, encoding="utf-8")
    if status.err:
        raise RuntimeError(f"PDF generation failed with {status.err} error(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PDF docs from Markdown")
    parser.add_argument(
        "--input",
        type=Path,
        action="append",
        help="Markdown file(s) to convert (default: all docs/*.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for PDFs",
    )
    args = parser.parse_args()

    inputs = args.input or sorted(DOCS_DIR.glob("*.md"))
    if not inputs:
        print("No markdown files found in docs/", file=sys.stderr)
        return 1

    generated: list[Path] = []
    for input_path in inputs:
        input_path = input_path.resolve()
        if not input_path.exists():
            print(f"Skip (not found): {input_path}", file=sys.stderr)
            continue
        output_path = args.output_dir / f"{input_path.stem}.pdf"
        print(f"Generating {output_path} ...")
        md_to_pdf(input_path, output_path)
        generated.append(output_path)
        print(f"  OK ({output_path.stat().st_size // 1024} KB)")

    if not generated:
        return 1

    print(f"\nDone. {len(generated)} PDF(s) written to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
