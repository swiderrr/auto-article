#!/usr/bin/env python3
import os
import sys
import requests

# Set API key
PEXELS_API_KEY = "Px0ZCETEZa0Q15pcuyVqM2Jo16xeU8O7j2SUKkvxX4hiU0oW8ESo6mO9"

headers = {"Authorization": PEXELS_API_KEY}
params = {
    "query": "infant vaccination pediatrician",
    "per_page": 10,
    "orientation": "landscape",
    "size": "large"
}

print("Testing Pexels API with improved filtering...")
r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
r.raise_for_status()
res = r.json()
photos = res.get('photos', [])

print(f"\nFound {len(photos)} photos\n")

# Filter logic from generate_article.py
filtered = []
for p in photos:
    desc = (p.get('alt', '') + ' ' + p.get('description', '')).lower()
    url_lower = p.get('url', '').lower()
    
    skip_keywords = [
        'disaster', 'earthquake', 'accident', 'crying', 'sad',
        'tights', 'stockings', 'legwear', 'pantyhose', 'hosiery',
        'tower', 'electrical', 'power', 'transmission', 'pylon',
        'building', 'architecture', 'city', 'urban', 'skyline',
        'fashion', 'model', 'sexy', 'lingerie', 'adult',
        'abstract', 'pattern', 'texture', 'background',
        'mountain', 'landscape', 'ocean', 'beach', 'sunset'
    ]
    
    required_keywords = ['baby', 'infant', 'child', 'toddler', 'parent', 'mother', 
                        'father', 'family', 'pediatric', 'newborn']
    
    has_required = any(kw in desc or kw in url_lower for kw in required_keywords)
    has_skip = any(kw in desc or kw in url_lower for kw in skip_keywords)
    
    status = "✓" if (has_required and not has_skip) else "✗"
    reason = ""
    if has_skip:
        reason = f" (skip keyword found)"
    elif not has_required:
        reason = f" (no required keyword)"
    
    print(f"{status} {desc[:60]}{reason}")
    
    if has_required and not has_skip:
        filtered.append(p)

print(f"\n✓ Passed filter: {len(filtered)}/{len(photos)} images")
