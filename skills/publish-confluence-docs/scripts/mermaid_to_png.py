#!/usr/bin/env python3
"""Extract Mermaid diagrams from Markdown and render to PNG.

Usage:
    python3 mermaid_to_png.py input.md [--output-dir DIR] [--width WIDTH] [--scale SCALE]

Extracts all ```mermaid blocks from the markdown file, writes .mmd files,
and renders each to PNG using @mermaid-js/mermaid-cli (mmdc).

Prerequisites:
    Install package.json from this skill's root with npm install.

Output files are named based on the heading preceding each mermaid block,
or diagram_1.png, diagram_2.png if no heading found.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

def extract_mermaid_blocks(md_path):
    with open(md_path, 'r') as f:
        content = f.read()
    blocks = []
    # Find each mermaid block with the nearest preceding heading
    for m in re.finditer(r'```mermaid\n(.*?)```', content, re.DOTALL):
        preceding = content[:m.start()]
        headings = re.findall(r'#+\s+(.+)', preceding)
        name = headings[-1] if headings else f'diagram_{len(blocks)+1}'
        # Sanitize name for filename
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', name).strip('_')
        blocks.append((safe, m.group(1).strip()))
    return blocks

def render(blocks, output_dir, width, scale):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for name, mermaid_src in blocks:
        mmd_path = os.path.join(output_dir, f'{name}.mmd')
        png_path = os.path.join(output_dir, f'{name}.png')
        with open(mmd_path, 'w') as f:
            f.write(mermaid_src)
        cmd = ['npx', '--no-install', '--prefix', str(Path(__file__).resolve().parents[1]), 'mmdc', '-i', mmd_path, '-o', png_path, '-b', 'white', '-w', str(width), '-s', str(scale)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(png_path):
            size = os.path.getsize(png_path)
            print(f"OK: {png_path} ({size} bytes)")
            results.append(png_path)
        else:
            print(f"FAIL: {name} — {r.stderr}", file=sys.stderr)
    return results

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', help='Markdown file with mermaid blocks')
    p.add_argument('--output-dir', default=None, help='Output directory (default: same as input)')
    p.add_argument('--width', type=int, default=1600, help='Image width in pixels (default: 1600)')
    p.add_argument('--scale', type=int, default=2, help='Scale factor for retina (default: 2)')
    args = p.parse_args()
    out = args.output_dir or os.path.dirname(os.path.abspath(args.input))
    blocks = extract_mermaid_blocks(args.input)
    print(f"Found {len(blocks)} mermaid block(s)")
    render(blocks, out, args.width, args.scale)
