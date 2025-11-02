
#!/usr/bin/env python3
import os
import sys
import datetime
import subprocess
import re
import json
from openai import OpenAI
import requests
import random
import time
from advanced_seo import AdvancedSEOHelper
from PIL import Image
import yaml

# Initialize Advanced SEO helper
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
seo = AdvancedSEOHelper(base)

# Load .env file from project kids/ directory (if present) so users can put keys in `kids/.env`
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(base, ".env")
if os.path.exists(dotenv_path):
    try:
        with open(dotenv_path, encoding="utf-8") as df:
            for line in df:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('\"\'')
                    # don't overwrite existing environment variables
                    os.environ.setdefault(k, v)
    except Exception:
        pass

# Read API keys from environment for safety
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set. The script can run in dry-run mode but cannot generate articles.")

client = None
if OpenAI and OPENAI_API_KEY:
    # defer instantiation until first use
    client = None
elif not OpenAI and OPENAI_API_KEY:
    print("openai package not installed; will use HTTP requests to OpenAI API if network is available.")
elif not OpenAI:
    print("openai package not installed; running in dry-run mode unless OPENAI_API_KEY and package are available.")


def call_openai(prompt, model="gpt-4.1-nano", max_tokens=2000):
    """Call OpenAI either via the python SDK (if available) or via direct HTTP request.
    Returns the raw text output or None on failure.
    """
    global client
    if OpenAI and OPENAI_API_KEY:
        if client is None:
            client = OpenAI(api_key=OPENAI_API_KEY)
        try:
            resp = client.responses.create(model=model, input=prompt, max_output_tokens=max_tokens)
            text = getattr(resp, "output_text", None)
            if not text:
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = None
            return text
        except Exception as e:
            print("OpenAI SDK call failed:", e)
            return None
    elif OPENAI_API_KEY:
        # fallback to direct HTTP call
        url = "https://api.openai.com/v1/responses"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "input": prompt, "max_output_tokens": max_tokens}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            j = r.json()
            text = j.get("output_text")
            if not text:
                try:
                    text = j["output"][0]["content"][0]["text"]
                except Exception:
                    parts = []
                    for out in j.get("output", []):
                        for c in out.get("content", []):
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                parts.append(c.get("text", ""))
                    text = "\n".join(parts) if parts else None
            return text
        except Exception as e:
            print("OpenAI HTTP request failed:", e)
            return None
    else:
        return None

def slugify(text):
    s = text.lower()
    s = re.sub(r'[^a-z0-9\- ]', '', s)
    s = s.replace(' ', '-')
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def generate_article(topic, tone="neutral", length=700):
    prompt = f'''Napisz artykuł o temacie "{topic}" w poniższym dokładnym formacie JSON (bez dodatkowego tekstu):

{{
    "title": "Tytuł zoptymalizowany pod SEO z głównym słowem kluczowym",
    "summary": "2-3 zdania zawierające główne słowo kluczowe i powiązane terminy",
    "tags": ["8-12 tagów związanych z tematem"],
    "categories": ["2-3 kategorie"],
    "body": "Pełna treść w markdown",
    "seo_title": "Alternatywny tytuł SEO",
    "seo_description": "Meta opis dla wyszukiwarek"
}}

Wymagania treści:
- Pisz po polsku
- Tytuł musi zawierać główne słowo kluczowe
- Wybierz 2-3 kategorie z: ["Rodzicielstwo", "Zdrowie", "Rozwój dziecka", "Ciąża i poród", "Produkty dla dzieci"]
- Dodaj 8-12 istotnych tagów SEO
- Długość treści: {length} słów
- Format markdown z nagłówkami ## i ###
- Dodaj znaczniki [IMAGE-1] do [IMAGE-4] w miejscach gdzie pasują zdjęcia
- Pisz przyjaznym tonem dla rodziców

Struktura artykułu:
- Wstęp (z [IMAGE-1])
- Sekcja Co/Dlaczego wyjaśniająca temat (z [IMAGE-2])
- Sekcja Jak z praktycznymi krokami (z [IMAGE-3])
- Wskazówki i rekomendacje (z [IMAGE-4])
- Podsumowanie

W każdej sekcji:
- Używaj praktycznych przykładów
- Dodaj listy punktowane gdzie to ma sens
- Pisz w sposób zaangażowany i pomocny
- Używaj słów kluczowych naturalnie w tekście
'''
    text = call_openai(prompt, model="gpt-4.1-nano", max_tokens=2000)
    if not text:
        print("No OpenAI response available. Returning dry-run stub article.")
        return {
            "title": f"{topic}",
            "summary": "(dry-run)",
            "tags": ["automated", "dry-run"],
            "categories": ["Rozwój dziecka"],
            "seo_title": f"{topic}",
            "seo_description": "Artykuł testowy - tryb dry-run",
            "body": f"# {topic}\n\nTreść wygenerowana w trybie dry-run."
        }

    # Parse JSON response
    try:
        # Find first { and last } to extract JSON
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON structure found in response")
        json_text = text[json_start:json_end]
        # Clean control characters and normalize whitespace
        json_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', json_text)
        json_text = re.sub(r'\s+', ' ', json_text)

        # Try to load JSON, and on failure provide helpful diagnostics and a small set of auto-fixes
        try:
            # First try a direct load
            data = json.loads(json_text)
        except json.JSONDecodeError as je:
            # Attempt a simple fix: remove trailing commas before } or ] which commonly break JSON
            fixed = re.sub(r',\s*([}\]])', r'\1', json_text)
            # Also fix common accidental empty-string tokens inserted between fields, e.g. '" " , "seo_title"'
            fixed = re.sub(r'"\s*"\s*,\s*"', '", "', fixed)
            try:
                data = json.loads(fixed)
                json_text = fixed
            except json.JSONDecodeError:
                # Provide contextual debug info to help identify the problem
                err_pos = getattr(je, 'pos', None)
                msg = str(je)
                print(f"Error: {msg}")
                if err_pos is not None:
                    start = max(0, err_pos - 200)
                    end = min(len(json_text), err_pos + 200)
                    context = json_text[start:end]
                    pointer = ' ' * (err_pos - start) + '^'
                    print("--- JSON parsing error context (snippet around error) ---")
                    print(context)
                    print(pointer)
                else:
                    print("--- JSON snippet (first 2000 chars) ---")
                    print(json_text[:2000])

                # Save problematic JSON to a temp file for easier inspection
                try:
                    tmp_path = os.path.join('/tmp', f'bad_ai_json_{int(time.time())}.json')
                    with open(tmp_path, 'w', encoding='utf-8') as tf:
                        tf.write(json_text)
                    print(f"Saved problematic JSON to: {tmp_path}")
                except Exception:
                    pass

                # Re-raise as ValueError to be caught by outer handler
                raise

        # Check required fields
        required_fields = ["title", "body", "summary", "tags", "categories"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Clean content from code blocks and artifacts
        body = re.sub(r"```[^`]*```", "", data["body"], flags=re.DOTALL)
        body = re.sub(r"`{1,2}[^`]*`{1,2}", "", body)
        # Replace bare Markdown image tags without URLs (e.g. `![Alt text]`) with numbered placeholders [IMAGE-1]
        # Keep images that have a URL in the form ![alt](url) untouched.
        def _replace_bare_images(text):
            imgs = []
            # Match ![alt] when NOT followed by '(' (i.e., no URL)
            def _repl(m):
                imgs.append(m.group(1).strip())
                return f"[IMAGE-{len(imgs)}]"

            return re.sub(r'!\[([^\]]*)\](?!\()', _repl, text)

        body = _replace_bare_images(body)
        data["body"] = body.strip()

        # Ensure fields are of correct type
        if not isinstance(data.get("tags", []), list):
            data["tags"] = [tag.strip() for tag in str(data.get("tags", "")).split(",") if tag.strip()]
        if not isinstance(data.get("categories", []), list):
            data["categories"] = [cat.strip() for cat in str(data.get("categories", "")).split(",") if cat.strip()]

        # Add default values for optional SEO fields
        data.setdefault("seo_title", data["title"])
        data.setdefault("seo_description", data["summary"])

    except ValueError as ve:
        print(f"Error: {str(ve)}")
        return None
    except json.JSONDecodeError as je:
        print(f"Error: Invalid JSON format: {str(je)}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error while processing response: {str(e)}")
        return None

    print(f"Successfully generated article: {data['title']}")
    return data

def make_markdown_file(data):
    # Generate SEO metadata and suggestions
    meta_tags = seo.generate_meta_tags(data.get('title', ''), data.get('summary', ''))
    structured_data = seo.generate_structured_data(data)
    seo_analysis = seo.analyze_content(data.get('body', ''))
    
    # Get internal linking suggestions
    slug = slugify(data.get('title', 'article'))
    internal_links = seo.get_internal_linking_suggestions(data.get('body', ''), slug)
    
    # Add internal links if found
    if internal_links:
        data['body'] += "\n\n## Zobacz także\n\n"
        for link in internal_links:
            data['body'] += f"- [{link['title']}](/posts/{os.path.splitext(link['file'])[0]})\n"
    
    # base dir is two levels up from this script (kids/)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Use timezone-aware UTC datetimes
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(data.get("title","article"))
    filename = os.path.join(base, "content", "posts", f"{date}-{slug}.md")
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # przygotuj front-matter YAML
    cats = data.get('categories', [])
    if isinstance(cats, str):
        cats = [cats]
    tags = data.get('tags', [])
    if not isinstance(tags, list):
        tags = [tags]

    cats_str = ', '.join(f'"{c}"' for c in cats)
    tags_str = ', '.join(f'"{t}"' for t in tags)

    # Generate optimized meta tags for SEO
    title = data.get('title', '')
    optimized_title = seo.optimize_title(title, data.get('tags', []))
    meta_desc = seo.generate_meta_description(data.get('body', ''), data.get('tags', []))
    social_meta = seo.generate_social_meta(data)
    structured_data = seo.generate_structured_data(data)
    
    # Optimize content structure
    data['body'] = seo.optimize_headers(data.get('body', ''))

    # --- Affiliate insertion rules ---
    affiliate_items = []
    try:
        aff_file = os.path.join(base, 'data', 'affiliate.yaml')
        if os.path.exists(aff_file):
            with open(aff_file, 'r', encoding='utf-8') as af:
                aff_data = yaml.safe_load(af)
                # aff_data may be a list or nested; normalize
                if isinstance(aff_data, list):
                    for entry in aff_data:
                        if isinstance(entry, dict):
                            affiliate_items.append(entry)
                elif isinstance(aff_data, dict):
                    # older format: wrap
                    affiliate_items = [aff_data]
    except Exception as e:
        print('Failed to load affiliate data:', e)

    # Find matching affiliate items and prepare insertion
    matched_affiliates = []
    body_lower = data.get('body','').lower()
    for item in affiliate_items:
        kws = item.get('keywords', []) or []
        for kw in kws:
            if kw.lower() in body_lower:
                matched_affiliates.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'url': item.get('url'),
                    'note': item.get('note','')
                })
                break

    # Insert affiliate block near 'Wskazówki' section if present; otherwise append to end
    if matched_affiliates:
        aff_md_lines = ['\n## Rekomendacje produktów i afiliacje\n']
        for m in matched_affiliates:
            aff_md_lines.append(f"- **{m.get('name','Produkt')}** — {m.get('note','')} [Kup teraz]({m.get('url')})")
        aff_md = '\n'.join(aff_md_lines) + '\n'

        body = data.get('body','')
        # try to find 'Wskazówki i rekomendacje' or 'Wskazówki'
        insert_at = None
        lower = body.lower()
        if '## wskazówki i rekomendacje' in lower:
            insert_at = body.lower().index('## wskazówki i rekomendacje')
        elif '## wskazówki' in lower:
            insert_at = body.lower().index('## wskazówki')

        if insert_at is not None:
            # insert after that heading block (find next double newline)
            # find the heading in original case:
            idx = insert_at
            # find next occurrence of '\n\n' after heading
            next_break = body.find('\n\n', idx)
            if next_break != -1:
                # insert after the first paragraph following heading
                body = body[:next_break+2] + aff_md + body[next_break+2:]
            else:
                body = body + '\n' + aff_md
        else:
            body = body + '\n' + aff_md

        data['affiliate_links'] = matched_affiliates
        data['body'] = body
    
    fm = [
        "---",
        f"title: \"{optimized_title}\"",
        f"date: {date}",
        "draft: false",
        f"tags: [{tags_str}]",
        f"categories: [{cats_str}]",
        f"summary: \"{data.get('summary','')}\"",
        "authors: [\"Poradnik Rodzica\"]",
        "ai_generated: true",
        f"ai_disclaimer: \"{('Artykuł wygenerowany z pomocą sztucznej inteligencji. Prosimy o weryfikację treści, szczególnie porad medycznych i prawnych.') }\"",
        f"featured_image: \"{data.get('featured_image','')}\"",
        f"description: \"{meta_desc}\"",
        "seo:",
        f"  title: \"{meta_tags['title']}\"",
        f"  description: \"{meta_tags['description']}\"",
        "  twitter:",
        f"    title: \"{meta_tags['twitter:title']}\"",
        f"    description: \"{meta_tags['twitter:description']}\"",
        "  og:",
        f"    title: \"{meta_tags['og:title']}\"",
        f"    description: \"{meta_tags['og:description']}\"",
        "structured_data: |",
        "  " + json.dumps(seo.generate_structured_data(data), indent=2).replace('\n', '\n  '),
        "---",
        "",
        data.get("body", "")
    ]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(fm))
    return filename

def git_commit_and_push(path, message="Add AI article"):
    subprocess.check_call(["git", "add", path])
    subprocess.check_call(["git", "commit", "-m", message])
    subprocess.check_call(["git", "push", "origin", "HEAD"])

if __name__ == "__main__":
    # CLI: optional topic arg; otherwise pick a random line from topics.txt
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: generate_article.py [\"Topic text\"]\n\nIf no topic is provided, a random topic is selected from topics.txt.\nSet OPENAI_API_KEY and PEXELS_API_KEY environment variables to enable generation and image download.")
        sys.exit(0)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    topics_file = os.path.join(base, "topics.txt")
    topic = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        topic = sys.argv[1]
    else:
        try:
            with open(topics_file, encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            if lines:
                topic = random.choice(lines)
        except FileNotFoundError:
            topic = "Sztuczna inteligencja w DevOps"

    data = generate_article(topic)
    if not data:
        print("Article generation failed or invalid. Exiting.")
        sys.exit(1)

    # Try to download images from Pexels if API key is available
    slug = slugify(data.get('title', 'article'))
    img_dir = os.path.join(base, "static", "img", "generated", slug)
    if PEXELS_API_KEY:
        os.makedirs(img_dir, exist_ok=True)
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
            """Download images from Pexels with content filtering and metadata capture."""
            headers = {"Authorization": PEXELS_API_KEY}
            # Enhance search query for better results
            safe_terms = {
                "diet": "healthy food baby",
                "karmienie": "baby feeding",
                "jedzenie": "baby food",
                "posiłek": "baby meal",
                "niemowlę": "happy baby",
                "dziecko": "happy child",
            }
            safe_query = query
            for k, v in safe_terms.items():
                if k.lower() in query.lower():
                    safe_query = v
                    break
            
            params = {
                "query": safe_query,
                "per_page": per_page * 2,  # Get more to filter
                "orientation": "landscape",
                "size": "large"
            }
            try:
                r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
                r.raise_for_status()
                res = r.json()
                photos = res.get('photos', [])
                
                # Filter photos to avoid inappropriate content
                filtered_photos = []
                for p in photos:
                    # Skip photos with unwanted keywords in their description
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
                        # Basic validation
                        if not _is_image_suitable(path):
                            # remove unsuitable image
                            try:
                                os.remove(path)
                            except Exception:
                                pass
                            continue

                        # Save image metadata
                        meta = {
                            "provider": "Pexels",
                            "photographer": p.get('photographer'),
                            "photographer_url": p.get('photographer_url'),
                            "source_url": p.get('url'),
                            "license": "Pexels License",
                            "license_url": "https://www.pexels.com/license/",
                            "description": p.get('alt') or p.get('description', ''),
                            "downloaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }
                        meta_path = os.path.splitext(path)[0] + '.json'
                        with open(meta_path, 'w', encoding='utf-8') as f:
                            json.dump(meta, f, ensure_ascii=False, indent=2)
                            
                        saved.append({
                            'filename': fn,
                            'description': p.get('alt') or p.get('description', ''),
                            'photographer': p.get('photographer'),
                        })
                        time.sleep(0.2)
                    except Exception as e:
                        print(f"Failed to download image {fn}:", e)
                return saved
            except Exception as e:
                print("Pexels search failed:", e)
                return []

        def download_unsplash(query, per_page=4):
            """Fallback to Unsplash public API via source.unsplash.com when API key not available.
            This uses the unsplash source endpoint to fetch random images for a query.
            """
            saved = []
            for i in range(per_page):
                try:
                    # Use source.unsplash.com to get a relevant image
                    url = f"https://source.unsplash.com/1600x900/?{requests.utils.quote(query)}"
                    rr = requests.get(url, timeout=30)
                    rr.raise_for_status()
                    # unsplash redirects to a final image URL
                    final_url = rr.url
                    ext = os.path.splitext(final_url.split('?')[0])[1] or '.jpg'
                    fn = f"img_unsplash_{i}{ext}"
                    path = os.path.join(img_dir, fn)
                    rr2 = requests.get(final_url, timeout=30)
                    rr2.raise_for_status()
                    with open(path, 'wb') as f:
                        f.write(rr2.content)
                    if not _is_image_suitable(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                        continue

                    meta = {
                        "provider": "Unsplash",
                        "photographer": "Unsplash",
                        "photographer_url": "https://unsplash.com",
                        "source_url": final_url,
                        "license": "Unsplash License",
                        "license_url": "https://unsplash.com/license",
                        "description": query,
                        "downloaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    meta_path = os.path.splitext(path)[0] + '.json'
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    saved.append({'filename': fn, 'description': query, 'photographer': 'Unsplash'})
                    time.sleep(0.2)
                except Exception as e:
                    print("Unsplash fetch failed:", e)
            return saved

        imgs = download_pexels(topic, per_page=4)
        if not imgs:
            # try Unsplash fallback
            print("Pexels returned no suitable images; trying Unsplash fallback")
            imgs = download_unsplash(topic, per_page=4)

        if imgs:
            # Set featured image to first saved (use relative path without leading slash so URLs
            # are correct when the site is served from a subpath on GitHub Pages)
            data['featured_image'] = f"img/generated/{slug}/{imgs[0]['filename']}"
            
            # Replace [IMAGE-n] placeholders with actual images or add them in logical places
            body = data.get('body', '')
            for i, img in enumerate(imgs):
                placeholder = f"[IMAGE-{i+1}]"
                # sanitize attribute values to avoid smart quotes and embedded newlines
                def _sanitize_attr(s):
                    if not s:
                        return ""
                    v = str(s)
                    # normalize smart quotes to straight quotes
                    v = v.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
                    v = v.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                    # collapse whitespace and remove newlines
                    v = ' '.join(v.split())
                    # escape double quotes for shortcode attributes
                    v = v.replace('"', '\\"')
                    return v

                alt_text = _sanitize_attr(img.get('description') or '')
                photographer = _sanitize_attr(img.get('photographer') or '')
                caption_text = _sanitize_attr((img.get('description') or '') + (f" (Photo: {img.get('photographer')})" if img.get('photographer') else ''))

                img_md = (
                    "\n\n{{< figure src=\"img/generated/" + slug + "/" + img['filename'] + "\" "
                    "alt=\"" + alt_text + "\" "
                    "caption=\"" + caption_text + "\" "
                    "class=\"article-image\" >}}\n\n"
                )

                if placeholder in body:
                    body = body.replace(placeholder, img_md)
                elif i == 0:
                    # First image goes at the top if no placeholder
                    body = img_md + body
                else:
                    # Find a paragraph break to insert the image
                    parts = body.split("\n\n")
                    if len(parts) > i+1:
                        parts.insert(i+1, img_md)
                        body = "\n\n".join(parts)
            data['body'] = body
    else:
        print("PEXELS_API_KEY not set; skipping image download. To enable image download set PEXELS_API_KEY env var.")

    # Insert visible AI disclosure at top of body if generated by AI
    if data.get('ai_generated'):
        disclosure = (
            "**Uwaga:** Ten artykuł został wygenerowany przy użyciu narzędzi sztucznej inteligencji. "
            "Treść ma charakter informacyjny — w szczególnych przypadkach (np. porady medyczne, prawne) "
            "prosimy o dodatkową weryfikację u specjalisty."
        )
        # Put disclosure after first heading or at the top
        body = data.get('body', '')
        if body.startswith('#'):
            # insert after first newline
            parts = body.split('\n', 2)
            if len(parts) >= 3:
                body = parts[0] + '\n' + '\n' + f'> {disclosure}' + '\n\n' + parts[2]
            else:
                body = f'> {disclosure}\n\n' + body
        else:
            body = f'> {disclosure}\n\n' + body
        data['body'] = body

    md = make_markdown_file(data)
    print("Saved:", md)
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        git_commit_and_push(md, f"Automated: {data.get('title')}")
