#!/usr/bin/env python3
"""
Generate a static index.html at repository root from the Flask template + config.yaml.
Run this script before committing to update the GitHub Pages build.
"""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "templates" / "index.html"
CONFIG   = ROOT / "config.yaml"
OUT_INDEX = ROOT / "index.html"

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

# Write static page at repository root for GitHub Pages deployment
OUT_INDEX.write_text(html)
print(f"Wrote {OUT_INDEX}")

# Ensure static assets exist where index.html expects them
static_src = ROOT / "static"
if not static_src.exists():
    raise FileNotFoundError("Expected static/ directory was not found")
print("Using existing static/ assets")
