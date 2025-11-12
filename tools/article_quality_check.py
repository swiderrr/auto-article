#!/usr/bin/env python3
"""Simple quality checker for Hugo content files.

Checks per-article:
 - presence and length of seo.description or summary (120-160 chars preferred)
 - word count of content (min 600 words)
 - presence of featured_image or params.featured_image
 - presence of authors

Outputs a JSON report and prints a human-readable summary.
"""
import sys
import os
import re
import json
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / 'kids' / 'content'

MIN_WORDS = 600
MIN_META_DESC = 120
MAX_META_DESC = 160


def count_words(markdown_text):
    # Strip frontmatter and shortcodes; approximate by counting word chars
    text = re.sub(r"```[\s\S]*?```", "", markdown_text)
    text = re.sub(r"<[^>]+>", "", text)
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return len(words)


def check_file(path: Path):
    post = frontmatter.load(path)
    body = post.content or ''
    word_count = count_words(body)

    # description
    seo = post.get('seo', {}) or {}
    description = seo.get('description') or seo.get('meta_description') or post.get('summary') or post.get('description')
    desc_len = len(description or '')

    featured = post.get('featured_image') or post.get('featured') or False
    authors = post.get('authors') or post.get('author')

    issues = []
    if not description:
        issues.append('missing_meta_description')
    else:
        if desc_len < MIN_META_DESC:
            issues.append(f'meta_description_too_short ({desc_len} chars)')
        if desc_len > MAX_META_DESC:
            issues.append(f'meta_description_too_long ({desc_len} chars)')

    if word_count < MIN_WORDS:
        issues.append(f'too_short ({word_count} words)')

    if not featured:
        issues.append('missing_featured_image')

    if not authors:
        issues.append('missing_author')

    return {
        'path': str(path.relative_to(ROOT)),
        'title': post.get('title'),
        'word_count': word_count,
        'meta_description_length': desc_len,
        'has_featured_image': bool(featured),
        'authors': authors,
        'issues': issues,
    }


def main():
    results = []
    for p in CONTENT_DIR.rglob('*.md'):
        results.append(check_file(p))

    out = {
        'summary': {
            'checked': len(results),
            'min_words': MIN_WORDS,
            'preferred_meta_range': [MIN_META_DESC, MAX_META_DESC]
        },
        'results': results
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))

    # Print short human summary
    bad = [r for r in results if r['issues']]
    print(f"\nChecked {len(results)} files, {len(bad)} have issues:")
    for r in bad[:20]:
        print(f" - {r['path']}: {', '.join(r['issues'])}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
