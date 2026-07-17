#!/usr/bin/env python3
"""Basic CSS minifier for the project's global stylesheet.

Produces static/css/global/style.min.css from static/css/global/style.css
This is a simple whitespace/comment remover — for best results run a proper
CSS build step (postcss/clean-css) in CI, but this reduces size immediately.
"""
from pathlib import Path
import re
import sys


def minify(css_text: str) -> str:
    # remove comments
    css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    # collapse whitespace
    css_text = re.sub(r'\s+', ' ', css_text)
    # remove space around symbols
    css_text = re.sub(r'\s*([{}:;,])\s*', r"\1", css_text)
    # remove final semicolon before }
    css_text = re.sub(r';}', '}', css_text)
    return css_text.strip()


def main():
    base = Path(__file__).resolve().parent.parent
    src = base / 'static' / 'css' / 'global' / 'style.css'
    if not src.exists():
        print('global style.css not found:', src)
        sys.exit(1)

    dst = src.parent / 'style.min.css'
    text = src.read_text(encoding='utf-8')
    minified = minify(text)
    dst.write_text(minified, encoding='utf-8')
    print('Wrote', dst)


if __name__ == '__main__':
    main()
