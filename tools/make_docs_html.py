# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""
Erzeugt installer/docs/LIESMICH.html und installer/docs/AENDERUNGEN.html
aus README.md und CHANGELOG.md.

Build-Zeit-Werkzeug — gehört NICHT in requirements.txt (App).
Abhängigkeit: markdown>=3.0 (requirements-dev.txt).

Aufruf: python tools/make_docs_html.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print(
        "Fehler: 'markdown' nicht installiert.\n"
        "  pip install markdown\n"
        "Oder alle Dev-Abhaengigkeiten: pip install -r requirements-dev.txt",
        file=sys.stderr,
    )
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "installer" / "docs"

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      max-width: 920px;
      margin: 0 auto;
      padding: 2em 1.5em;
      color: #1a1a1a;
      background: #ffffff;
    }}
    h1, h2, h3, h4, h5 {{ color: #1a3a6b; margin-top: 1.4em; margin-bottom: 0.4em; }}
    h1 {{ font-size: 1.8em; border-bottom: 2px solid #1a3a6b; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.35em; border-bottom: 1px solid #c0cce0; padding-bottom: 0.2em; }}
    h3 {{ font-size: 1.1em; }}
    a {{ color: #1a55a0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
      background: #f0f2f5;
      border: 1px solid #d0d7e0;
      border-radius: 3px;
      padding: 0.1em 0.35em;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.9em;
    }}
    pre {{
      background: #f6f8fa;
      border: 1px solid #d0d7e0;
      border-radius: 4px;
      padding: 0.8em 1em;
      overflow-x: auto;
    }}
    pre code {{
      background: none;
      border: none;
      padding: 0;
      font-size: 0.88em;
    }}
    table {{
      border-collapse: collapse;
      margin: 1em 0;
      width: 100%;
    }}
    th, td {{
      border: 1px solid #c8d0da;
      padding: 0.4em 0.75em;
      text-align: left;
    }}
    th {{ background: #e4ecf7; font-weight: 600; }}
    tr:nth-child(even) td {{ background: #f8fafc; }}
    hr {{ border: none; border-top: 1px solid #ccd4de; margin: 1.6em 0; }}
    ul, ol {{ padding-left: 1.6em; margin-top: 0.3em; }}
    li {{ margin-bottom: 0.25em; }}
    blockquote {{
      border-left: 4px solid #c0cce0;
      margin: 0.8em 0;
      padding: 0.3em 0.8em 0.3em 1em;
      color: #444;
      background: #f6f8fb;
    }}
    p {{ margin: 0.6em 0; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""

_MD_EXTENSIONS = [
    "fenced_code",   # ```-Codeblöcke
    "tables",        # Markdown-Tabellen
    "attr_list",     # {.class} Attribute (harmlos wenn nicht genutzt)
]


def _strip_unreleased_section(md_text: str) -> str:
    """Entfernt den ## [Unreleased]-Abschnitt aus CHANGELOG-Markdown.

    Für die Nutzer-HTML vollständig auslassen (leer oder gefüllt) — Endnutzer
    sehen nur veröffentlichte Versionen. CHANGELOG.md selbst bleibt unverändert.
    Robust gegenüber LF und CRLF.
    """
    out: list[str] = []
    skip = False
    for line in md_text.splitlines(keepends=True):
        if line.startswith("## [Unreleased]"):
            skip = True
            continue
        if skip and line.startswith("## ["):
            skip = False
        if not skip:
            out.append(line)
    return "".join(out)


def _md_to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=_MD_EXTENSIONS,
        output_format="html",
    )
    return _HTML_TEMPLATE.format(title=title, body=body)


def _convert(src: Path, dst: Path, title: str, preprocess=None) -> None:
    text = src.read_text(encoding="utf-8")
    if preprocess is not None:
        text = preprocess(text)
    html = _md_to_html(text, title)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html, encoding="utf-8")
    print(f"  {src.name:20s}  -->  {dst.relative_to(REPO_ROOT)}")


def main() -> None:
    print("Erzeuge HTML-Infodateien ...")
    _convert(
        REPO_ROOT / "README.md",
        OUT_DIR / "LIESMICH.html",
        "QSL73 – Liesmich",
    )
    _convert(
        REPO_ROOT / "CHANGELOG.md",
        OUT_DIR / "AENDERUNGEN.html",
        "QSL73 – Änderungshistorie",
        preprocess=_strip_unreleased_section,
    )
    print("Fertig.")


if __name__ == "__main__":
    main()
