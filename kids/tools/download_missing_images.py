import os
import glob
import requests
import json
import time
import datetime
from PIL import Image

def slugify(title):
    return title.lower().replace(' ', '-').replace('ą', 'a').replace('ć', 'c').replace('ę', 'e').replace('ł', 'l').replace('ń', 'n').replace('ó', 'o').replace('ś', 's').replace('ź', 'z').replace('ż', 'z').replace('?', '').replace('!', '').replace(',', '').replace('.', '').replace('---', '-').replace('--', '-')

PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
posts_dir = os.path.join(base, 'kids', 'content', 'posts')
img_base_dir = os.path.join(base, 'kids', 'static', 'img', 'generated')

# Find all post files
post_files = glob.glob(os.path.join(posts_dir, '*.md'))

for post_path in post_files:
    slug = os.path.splitext(os.path.basename(post_path))[0]
    img_dir = os.path.join(img_base_dir, slug)
    os.makedirs(img_dir, exist_ok=True)
    # Use post filename as topic
    topic = slug.replace('-', ' ')
    print(f"Downloading images for: {slug} -> {img_dir}")
    def _is_image_suitable(path, min_w=800, min_h=450, max_ratio=2.5):
        try:
            with Image.open(path) as im:
                w, h = im.size
                ratio = max(w / h, h / w)
                if w < min_w or h < min_h:
                    return False
                if ratio > max_ratio:
                    return False
            return True
        except Exception:
            return False
    def download_pexels(query, per_page=4):
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "per_page": per_page * 2,
            "orientation": "landscape",
            "size": "large"
        }
        try:
            r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
            r.raise_for_status()
            res = r.json()
            photos = res.get('photos', [])
            filtered_photos = []
            for p in photos:
                desc = (p.get('alt', '') + ' ' + p.get('description', '')).lower()
                skip_keywords = ['disaster', 'earthquake', 'accident', 'crying', 'sad']
                if any(kw in desc for kw in skip_keywords):
                    continue
                filtered_photos.append(p)
                if len(filtered_photos) >= per_page:
                    break
            saved = []
            for i, p in enumerate(filtered_photos[:per_page]):
                src = p.get('src', {}).get('large') or p.get('src', {}).get('original')
                if not src:
                    continue
                ext = os.path.splitext(src.split('?')[0])[1] or '.jpg'
                fn = f"img_{i}{ext}"
                path = os.path.join(img_dir, fn)
                try:
                    rr = requests.get(src, timeout=30)
                    rr.raise_for_status()
                    with open(path, 'wb') as f:
                        f.write(rr.content)
                    if not _is_image_suitable(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                        continue
                    meta = {
                        "provider": "Pexels",
                        "photographer": p.get('photographer'),
                        "photographer_url": p.get('photographer_url'),
                        "source_url": p.get('url'),
                        "license": "Pexels License",
                        "downloaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    meta_path = os.path.splitext(path)[0] + '.json'
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    saved.append({'filename': fn, 'description': topic, 'photographer': p.get('photographer')})
                    time.sleep(0.2)
                except Exception as e:
                    print("Pexels fetch failed:", e)
            return saved
        except Exception as e:
            print("Pexels API error:", e)
            return []
    def download_unsplash(query, per_page=4):
        # Fallback: download random images from Unsplash
        saved = []
        for i in range(per_page):
            url = f"https://source.unsplash.com/800x450/?{query.replace(' ', ',')}"
            fn = f"img_{i}.jpeg"
            path = os.path.join(img_dir, fn)
            try:
                rr = requests.get(url, timeout=30)
                rr.raise_for_status()
                with open(path, 'wb') as f:
                    f.write(rr.content)
                if not _is_image_suitable(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                    continue
                meta = {
                    "provider": "Unsplash",
                    "source_url": url,
                    "license": "Unsplash License",
                    "downloaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                meta_path = os.path.splitext(path)[0] + '.json'
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                saved.append({'filename': fn, 'description': topic, 'photographer': 'Unsplash'})
                time.sleep(0.2)
            except Exception as e:
                print("Unsplash fetch failed:", e)
        return saved
    imgs = []
    if PEXELS_API_KEY:
        imgs = download_pexels(topic, per_page=4)
    if not imgs:
        print("Pexels returned no suitable images; trying Unsplash fallback")
        imgs = download_unsplash(topic, per_page=4)
    print(f"Downloaded {len(imgs)} images for {slug}")
print("Done.")
