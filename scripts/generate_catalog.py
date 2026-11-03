#!/usr/bin/env python3
"""Build docs/catalog.json from images organized by directories."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'docs'
IMAGES = ROOT / 'images'
EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'}

def build():
    groups = []
    if IMAGES.exists():
        for folder in sorted(IMAGES.iterdir(), key=lambda p: p.name.lower()):
            if not folder.is_dir() or folder.name.startswith('.'):
                continue
            photos = [p for p in sorted(folder.rglob('*'), key=lambda p: str(p).lower())
                      if p.is_file() and p.suffix.lower() in EXTS]
            if photos:
                groups.append({
                    'id': folder.name,
                    'name': folder.name.replace('-', ' ').replace('_', ' ').title(),
                    'images': [p.relative_to(ROOT).as_posix() for p in photos]
                })
    payload = {'version': 1, 'groups': groups}
    target = ROOT / 'catalog.json'
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{target}: {len(groups)} groups, {sum(len(g["images"]) for g in groups)} images')

if __name__ == '__main__':
    build()
