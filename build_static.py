#!/usr/bin/env python3
"""
Generate a static docs/index.html from the Flask template + config.yaml.
Run this script before committing to update the GitHub Pages build.
"""
import json, re, shutil
from pathlib import Path
import yaml

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "templates" / "index.html"
CONFIG   = ROOT / "config.yaml"
DOCS     = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# Load config
with open(CONFIG) as f:
    cfg = yaml.safe_load(f)

config_json = json.dumps(cfg)

# Read template
html = TEMPLATE.read_text()

# Replace the single Jinja2 placeholder
html = html.replace("{{ config_json | safe }}", config_json)

# Fix absolute static path → relative (needed for GitHub Pages sub-path)
html = html.replace('src="/static/', 'src="static/')

# Write static page
out = DOCS / "index.html"
out.write_text(html)
print(f"Wrote {out}")

# Copy static assets
static_src = ROOT / "static"
static_dst = DOCS / "static"
if static_dst.exists():
    shutil.rmtree(static_dst)
shutil.copytree(static_src, static_dst)
print(f"Copied static/ → docs/static/")
