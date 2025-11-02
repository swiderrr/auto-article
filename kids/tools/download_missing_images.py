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
posts_dir = os.path.join(base, 'content', 'posts')
img_base_dir = os.path.join(base, 'static', 'img', 'generated')

# Find all post files
post_files = glob.glob(os.path.join(posts_dir, '*.md'))

for post_path in post_files:
    # Restore date prefix in slug and image directory
    slug = os.path.splitext(os.path.basename(post_path))[0]
    img_dir = os.path.join(img_base_dir, slug)
    topic = slug.replace('-', ' ')
    print(f"[INFO] Downloading images for: {slug} -> {img_dir}")
    print(f"[INFO] Topic: {topic}")
    try:
        os.makedirs(img_dir, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Could not create directory {img_dir}: {e}")
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
        print(f"[DEBUG] PEXELS_API_KEY: {PEXELS_API_KEY}")
        print(f"[INFO] Trying Pexels API for topic: {query}")
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "per_page": per_page * 2,
            "orientation": "landscape",
            "size": "large"
        }
        try:
            print(f"[DEBUG] Pexels request params: {params}")
            r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
            print(f"[DEBUG] Pexels request URL: {r.url}")
            print(f"[DEBUG] Pexels API status code: {r.status_code}")
            r.raise_for_status()
            res = r.json()
            photos = res.get('photos', [])
            print(f"[DEBUG] Pexels API returned {len(photos)} photos")
            filtered_photos = []
            if not photos:
                print(f"[WARN] No photos returned from Pexels API for topic: {query}")
            for p in photos:
                desc = (p.get('alt', '') + ' ' + p.get('description', '')).lower()
                skip_keywords = ['disaster', 'earthquake', 'accident', 'crying', 'sad']
                if any(kw in desc for kw in skip_keywords):
                    continue
                filtered_photos.append(p)
                if len(filtered_photos) >= per_page:
                    break
            print(f"[DEBUG] Filtered to {len(filtered_photos)} photos")
            saved = []
            for i, p in enumerate(filtered_photos[:per_page]):
                print(f"[DEBUG] Photo {i} meta: {json.dumps(p, ensure_ascii=False)}")
                src = p.get('src', {}).get('large') or p.get('src', {}).get('original')
                print(f"[DEBUG] Downloading image {i}: {src}")
                if not src:
                    print(f"[WARN] No src for image {i}")
                    continue
                ext = os.path.splitext(src.split('?')[0])[1] or '.jpg'
                fn = f"img_{i}{ext}"
                path = os.path.join(img_dir, fn)
                try:
                    print(f"[DEBUG] Downloading image {i} from {src}")
                    rr = requests.get(src, timeout=30)
                    print(f"[DEBUG] Image {i} download status: {rr.status_code}")
                    print(f"[DEBUG] Image {i} status code: {rr.status_code}")
                    rr.raise_for_status()
                    with open(path, 'wb') as f:
                        f.write(rr.content)
                    if not _is_image_suitable(path):
                        print(f"[WARN] Image {i} failed suitability check: {path}")
                        print(f"[WARN] Image {i} not suitable, removing")
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
                    print(f"[ERROR] Pexels fetch failed for image {i}: {e}")
            return saved
        except Exception as e:
            print(f"[ERROR] Pexels API error: {e}")
            return []
    def download_unsplash(query, per_page=4):
        print(f"[DEBUG] Unsplash fallback for topic: {query}")
        print(f"[INFO] Trying Unsplash fallback for topic: {query}")
        # Fallback: download random images from Unsplash
        saved = []
        for i in range(per_page):
            url = f"https://source.unsplash.com/800x450/?{query.replace(' ', ',')}"
            fn = f"img_{i}.jpeg"
            path = os.path.join(img_dir, fn)
            try:
                print(f"[DEBUG] Unsplash image URL: {url}")
                print(f"[DEBUG] Downloading Unsplash image {i}: {url}")
                rr = requests.get(url, timeout=30)
                print(f"[DEBUG] Unsplash image download status: {rr.status_code}")
                print(f"[DEBUG] Unsplash image {i} status code: {rr.status_code}")
                rr.raise_for_status()
                with open(path, 'wb') as f:
                    f.write(rr.content)
                if not _is_image_suitable(path):
                    print(f"[WARN] Unsplash image {i} failed suitability check: {path}")
                    print(f"[WARN] Unsplash image {i} not suitable, removing")
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
                print(f"[ERROR] Unsplash fetch failed for image {i}: {e}")
        return saved
    if PEXELS_API_KEY:
        imgs = download_pexels(topic, per_page=4)
    if not imgs:
        print("[INFO] Pexels returned no suitable images; trying Unsplash fallback")
        imgs = download_unsplash(topic, per_page=4)
    print(f"[RESULT] Downloaded {len(imgs)} images for {slug}")
print("Done.")
