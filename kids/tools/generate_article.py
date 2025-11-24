
#!/usr/bin/env python3
import os
import sys
import datetime
import subprocess
import re
import json
from openai import OpenAI
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import mimetypes
import requests
import random
import time
from advanced_seo import AdvancedSEOHelper
from PIL import Image
import toml
import yaml
from scientific_research import ScientificResearchManager

# Initialize Advanced SEO helper
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
seo = AdvancedSEOHelper(base)

# Load .env file from project kids/ directory (if present) so users can put keys in `kids/.env`
base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(base, ".env")

# Also check parent directory
if not os.path.exists(dotenv_path):
    parent_dotenv = os.path.join(os.path.dirname(base), ".env")
    if os.path.exists(parent_dotenv):
        dotenv_path = parent_dotenv

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

def generate_article(topic, tone="neutral", length=700, use_research=True):
    """
    Generate article with optional scientific research integration.
    
    Args:
        topic: Article topic
        tone: Writing tone
        length: Target length in words
        use_research: If True, search for and integrate scientific research
    
    Returns:
        Dict with article data including research if enabled
    """
    # First, search for relevant research if enabled
    research_list = []
    research_context = ""
    
    if use_research:
        print("🔬 Szukam badań naukowych związanych z tematem...")
        research_mgr = ScientificResearchManager()
        research_list = research_mgr.search_research(topic, count=3)
        
        if research_list:
            print(f"✓ Znaleziono {len(research_list)} badań")
            
            # Verify research (optional - can be time-consuming)
            verified_research = []
            for paper in research_list:
                print(f"  Weryfikuję: {paper.get('title', 'N/A')[:60]}...")
                verification = research_mgr.verify_research(paper)
                if verification.get('confidence', 0) > 50:
                    verified_research.append(paper)
                    print(f"    ✓ Zweryfikowano (pewność: {verification.get('confidence')}%)")
                else:
                    print(f"    ✗ Niska pewność ({verification.get('confidence')}%) - pominięto")
            
            research_list = verified_research
            
            # Build research context for article generation
            if research_list:
                research_context = "\n\nOPRZYJ ARTYKUŁ NA NASTĘPUJĄCYCH BADANIACH NAUKOWYCH:\n"
                for i, paper in enumerate(research_list, 1):
                    research_context += f"\n[{i}] {paper.get('title', 'N/A')}\n"
                    research_context += f"    Autorzy: {', '.join(paper.get('authors', []))}\n"
                    research_context += f"    Rok: {paper.get('year', 'N/A')}\n"
                    research_context += f"    Podsumowanie: {paper.get('summary', 'N/A')}\n"
                
                research_context += "\nW artykule odwołuj się do tych badań używając numerów w nawiasach kwadratowych, np. [1], [2].\n"
            else:
                print("❌ Nie znaleziono badań naukowych - artykuł nie zostanie wygenerowany.")
                print("💡 Spróbuj innego tematu związanego z:")
                print("   - rozwojem dziecka")
                print("   - zdrowiem niemowląt")
                print("   - karmieniem")
                print("   - snem dzieci")
                print("   - szczepionkami")
                return None
        else:
            print("⚠️  Nie znaleziono badań - generuję artykuł bez źródeł naukowych")
    
    prompt = f'''Napisz artykuł o temacie "{topic}" w poniższym dokładnym formacie JSON (bez dodatkowego tekstu):

{{
    "title": "Tytuł zoptymalizowany pod SEO z głównym słowem kluczowym",
    "summary": "2-3 zdania zawierające główne słowo kluczowe i powiązane terminy",
    "tags": ["8-12 tagów związanych z tematem"],
    "categories": ["2-3 kategorie"],
    "body": "Pełna treść w markdown",
    "seo_title": "Alternatywny tytuł SEO",
    "seo_description": "Meta opis dla wyszukiwarek (uwzględnij: oparty na badaniach naukowych)"
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
- WAŻNE: Jeśli podano badania naukowe, odwołuj się do nich w tekście używając [1], [2] itd.

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
{research_context}
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
        # Robust JSON extraction: find the first JSON object by scanning braces while
        # respecting quoted strings and escapes. This avoids grabbing trailing
        # non-JSON text that sometimes appears after the object (like '---' or
        # YAML frontmatter snippets) which breaks json.loads.
        def _extract_json_block(s):
            start = s.find('{')
            if start == -1:
                return None
            in_str = False
            esc = False
            depth = 0
            for i in range(start, len(s)):
                ch = s[i]
                if esc:
                    esc = False
                    continue
                if ch == '\\':
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return s[start:i+1]
            return None

        json_text = _extract_json_block(text)
        if not json_text:
            raise ValueError("No valid JSON structure found in response")
        # Remove non-printable control characters that might break the JSON parser,
        # but avoid collapsing all whitespace (preserve newlines inside strings if
        # they are escaped). Keep the original spacing otherwise.
        json_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', ' ', json_text)

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
    
    # Add research data to article
    if research_list:
        data['research'] = research_list
        data['has_research'] = True
    else:
        data['has_research'] = False
    
    return data

def make_markdown_file(data):
    # Generate SEO metadata and suggestions
    # Remove Hugo shortcodes (e.g. {{< figure ... >}}) from the body used for metadata
    raw_body = data.get('body', '')
    body_for_meta = re.sub(r'\{\{<[^>]*>\}\}', '', raw_body, flags=re.DOTALL)
    meta_tags = seo.generate_meta_tags(data.get('title', ''), data.get('summary', ''))
    structured_data = seo.generate_structured_data(data)
    seo_analysis = seo.analyze_content(body_for_meta)
    
    # Get internal linking suggestions
    # Restore date prefix in slug
    slug_full = slugify(data.get('title', 'article'))
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    slug = f"{date}-{slug_full}"
    internal_links = seo.get_internal_linking_suggestions(data.get('body', ''), slug)
    
    # Add internal links if found
    if internal_links:
        data['body'] += "\n\n## Zobacz także\n\n"
        for link in internal_links:
            data['body'] += f"- [{link['title']}](/posts/{os.path.splitext(link['file'])[0]})\n"
    
    # base dir is two levels up from this script (kids/)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Detect S3 base URL. Priority:
    # 1. env var S3_BASE_URL
    # 2. kids/.s3_migration_map.json mapping (use bucket + region or mapping values)
    # 3. kids/hugo.toml params.s3BaseURL
    s3_base = os.getenv('S3_BASE_URL')
    s3_map = {}
    try:
        s3_map_path = os.path.join(base, '.s3_migration_map.json')
        if os.path.exists(s3_map_path):
            with open(s3_map_path, 'r', encoding='utf-8') as smf:
                sm = json.load(smf)
                # mapping under 'mapping'
                if isinstance(sm, dict) and 'mapping' in sm:
                    s3_map = sm.get('mapping', {}) or {}
                # also allow bucket/region top-level to build base
                if not s3_base and sm.get('bucket') and sm.get('region'):
                    s3_base = f"https://{sm.get('bucket')}.s3.{sm.get('region')}.amazonaws.com"
    except Exception:
        s3_map = {}

    # Fallback: try to parse kids/hugo.toml for params.s3BaseURL
    if not s3_base:
        try:
            hugo_toml = os.path.join(base, 'hugo.toml')
            if os.path.exists(hugo_toml):
                parsed = toml.load(hugo_toml)
                s3_base = parsed.get('params', {}).get('s3BaseURL')
        except Exception:
            pass
    # Use timezone-aware UTC datetimes
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    filename = os.path.join(base, "content", "posts", f"{slug}.md")
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
    # Use sanitized body (without shortcodes) for meta description to avoid template artifacts
    meta_desc = seo.generate_meta_description(body_for_meta, data.get('tags', []))
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
                # store which keyword matched so we can replace it inline later
                matched_affiliates.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'url': item.get('url'),
                    'note': item.get('note',''),
                    'matched_keyword': kw
                })
                break

    # Fallback: jeśli nie znaleziono dopasowań na podstawie słów kluczowych,
    # wstaw losowo jeden link afiliacyjny (ułatwia testowanie i zapewnia, że
    # linki afiliacyjne są dodawane do nowych postów, nawet gdy brak dopasowań).
    if not matched_affiliates and affiliate_items:
        try:
            sample = random.choice(affiliate_items)
            matched_affiliates.append({
                'id': sample.get('id'),
                'name': sample.get('name'),
                'url': sample.get('url'),
                'note': sample.get('note', '')
            })
            # oznaczamy, że użyto fallbacku (przydatne do debugowania)
            data['affiliate_fallback_used'] = True
        except Exception:
            pass

    # Instead of adding a separate affiliate block, embed affiliate links naturally
    # inside the article text. We will allow multiple inserts per article to make
    # links more visible. Limits are configurable via environment variables:
    # AFFILIATE_MAX_INSERTS (default 4) - total anchors to insert in an article
    # AFFILIATE_PER_ITEM_MAX (default 2) - max anchors per affiliate item
    if matched_affiliates:
        body = data.get('body', '')

        # Configurable limits
        try:
            MAX_TOTAL_INSERTS = int(os.getenv('AFFILIATE_MAX_INSERTS', '4'))
        except Exception:
            MAX_TOTAL_INSERTS = 4
        try:
            PER_ITEM_MAX = int(os.getenv('AFFILIATE_PER_ITEM_MAX', '2'))
        except Exception:
            PER_ITEM_MAX = 2

        # Render mode: 'inline' (replace keywords) or 'block' (separate CTA lines).
        # Default to 'block' for greater visibility. Set AFFILIATE_RENDER_MODE=inline to keep inline behavior.
        RENDER_MODE = os.getenv('AFFILIATE_RENDER_MODE', 'block').lower()

        total_inserts = 0

        # Build list of CTAs (HTML) first — we'll distribute them across the post
        ctas_to_insert = []
        for m in matched_affiliates:
            if len(ctas_to_insert) >= MAX_TOTAL_INSERTS:
                break

            url = m.get('url') or ''
            name = m.get('name') or ''
            mk = m.get('matched_keyword')
            note = (m.get('note') or '').replace('"', '')
            title_attr = f' title="{note}"' if note else ''

            # inline anchor factory (for potential inline replacements)
            def make_anchor(text_label, affiliate_id=(m.get('id') or ''), affiliate_name=name, note=note):
                safe_name = str(affiliate_id).replace('"', '')
                title = f' title="{note}"' if note else ''
                return f'<a href="{url}" class="affiliate-link" data-affiliate-id="{safe_name}" data-affiliate-name="{affiliate_name}"{title} target="_blank" rel="sponsored noopener noreferrer">{text_label}</a>'

            # Create a prominent block CTA (button-like) with badge
            # Rotate CTA copy to increase engagement — choose from persuasive variants
            try:
                cta_variants = [
                    f"Zobacz ofertę: {name}",
                    f"Promocja: {name} — sprawdź",
                    f"Kup teraz: {name}",
                    f"Oferta: {name} — ograniczona ilość",
                    f"Sprawdź teraz: {name}",
                    f"Zobacz opinię i ofertę: {name}",
                ]
                cta_label = random.choice(cta_variants)
            except Exception:
                cta_label = f"Zobacz ofertę: {name}"

            cta_html = (
                f'<p class="affiliate-cta affiliate-cta--prominent">'
                f'<span class="affiliate-badge">Sponsorowane</span> '
                f'<a href="{url}" class="affiliate-cta__link" data-affiliate-name="{name}"{title_attr} target="_blank" rel="sponsored noopener noreferrer">{note}</a>'
                f'</p>'
            )

            ctas_to_insert.append({
                'html': cta_html,
                'mk': mk,
                'name': name,
                'url': url,
                'note': note
            })

        # If render mode is inline, attempt keyword/name replacements first (still limited)
        if RENDER_MODE == 'inline' and ctas_to_insert:
            body_parts = body.split('\n\n')
            for cta in list(ctas_to_insert):
                if total_inserts >= MAX_TOTAL_INSERTS:
                    break
                replaced = False
                if cta.get('mk'):
                    try:
                        pattern = re.compile(re.escape(cta['mk']), re.IGNORECASE)
                        for i, part in enumerate(body_parts):
                            if pattern.search(part):
                                body_parts[i], count = pattern.subn(lambda m: make_anchor(m.group(0)), body_parts[i], count=1)
                                if count:
                                    total_inserts += 1
                                    replaced = True
                                    break
                    except re.error:
                        pass

                if not replaced and cta.get('name'):
                    try:
                        pattern2 = re.compile(re.escape(cta['name']), re.IGNORECASE)
                        for i, part in enumerate(body_parts):
                            if pattern2.search(part):
                                body_parts[i], count2 = pattern2.subn(lambda m: make_anchor(m.group(0)), body_parts[i], count=1)
                                if count2:
                                    total_inserts += 1
                                    replaced = True
                                    break
                    except re.error:
                        pass

                if replaced:
                    ctas_to_insert.remove(cta)

            body = '\n\n'.join(body_parts)

        # Distribute remaining CTAs as prominent block CTAs evenly across paragraphs
        if ctas_to_insert:
            parts = body.split('\n\n')
            n = len(parts)
            if n <= 1:
                # just append all CTAs at start
                for cta in ctas_to_insert[:MAX_TOTAL_INSERTS - total_inserts]:
                    body = cta['html'] + '\n\n' + body
                    total_inserts += 1
            else:
                # choose evenly spaced insertion points
                slots = min(len(ctas_to_insert), MAX_TOTAL_INSERTS - total_inserts)
                step = max(1, n // (slots + 1))
                insert_positions = [step * i for i in range(1, slots + 1)]
                # ensure unique and within bounds
                insert_positions = [min(max(1, p), n) for p in insert_positions]
                # insert from last to first to keep indices valid
                for pos, cta in sorted(zip(insert_positions, ctas_to_insert[:slots]), reverse=True):
                    # insert after paragraph at index pos-1
                    idx = pos
                    parts.insert(idx, cta['html'])
                    total_inserts += 1

                body = '\n\n'.join(parts)

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
        f"ai_disclaimer: \"Artykuł wygenerowany przez AI na podstawie badań naukowych z baz medycznych: PubMed, Europe PMC, CrossRef, Semantic Scholar. Treści zostały zweryfikowane, jednak zalecamy konsultację ze specjalistą w przypadku konkretnych problemów zdrowotnych.\"",
        "research_databases: [\"PubMed\", \"Europe PMC\", \"CrossRef\", \"Semantic Scholar\"]",
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
    
    # Check if research mode is enabled (default: True)
    use_research = os.getenv('USE_RESEARCH', 'true').lower() in ('true', '1', 'yes')
    
    data = generate_article(topic, use_research=use_research)
    if not data:
        print("Article generation failed or invalid. Exiting.")
        sys.exit(1)

    # Try to download images from Pexels if API key is available
    slug_full = slugify(data.get('title', 'article'))
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    slug = f"{date}-{slug_full}"
    img_dir = os.path.join(base, "static", "img", "generated", slug)
    # Detect S3 base and mapping for main runtime (same logic as in make_markdown_file)
    s3_base = os.getenv('S3_BASE_URL')
    s3_map = {}
    try:
        s3_map_path = os.path.join(base, '.s3_migration_map.json')
        if os.path.exists(s3_map_path):
            with open(s3_map_path, 'r', encoding='utf-8') as smf:
                sm = json.load(smf)
                if isinstance(sm, dict) and 'mapping' in sm:
                    s3_map = sm.get('mapping', {}) or {}
                if not s3_base and sm.get('bucket') and sm.get('region'):
                    s3_base = f"https://{sm.get('bucket')}.s3.{sm.get('region')}.amazonaws.com"
    except Exception:
        s3_map = {}

    # Fallback: try to parse kids/hugo.toml for params.s3BaseURL
    if not s3_base:
        try:
            hugo_toml = os.path.join(base, 'hugo.toml')
            if os.path.exists(hugo_toml):
                parsed = toml.load(hugo_toml)
                s3_base = parsed.get('params', {}).get('s3BaseURL')
        except Exception:
            pass
    # First, try to use Sora-generated images
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
    
    # Download images - priority: Unsplash -> Pexels
    imgs = []
    
    def _translate_to_english(q):
        """Translate Polish terms to English for better image search results."""
        mapping = {
            r"\bpierwsz(e|a|y|ego|ych)\b": "first",
            r"\bkarmienie piersia\b": "baby breastfeeding mother",
            r"\bkarmienie piersią\b": "baby breastfeeding mother",
            r"\bbutelka\b": "baby bottle feeding",
            r"\brozszerzanie diety\b": "baby eating solid food",
            r"\bzasypianie\b": "baby sleeping",
            r"\bmetody zasypiania\b": "baby sleep routine",
            r"\bdrzemki\b": "baby napping",
            r"\bpiel(e|ę)gnacj(a|i|ą)\b": "baby care",
            r"\bpieluszki\b": "baby diaper changing",
            r"\bwyprawka\b": "baby nursery essentials",
            r"\bw[oó]zek\b": "baby stroller",
            r"\bfotelik\b": "baby car seat",
            r"\bkrzese(ł|l)ko do karmienia\b": "baby high chair",
            r"\bnocnik\b": "potty training toddler",
            r"\bkarmienie mieszane\b": "baby mixed feeding",
            r"\b[zż][łl]obek\b": "daycare children",
            r"\bprzedszkole\b": "preschool children",
            r"\bszczepie[ńn](|a|ia|iach|iu)\b": "infant vaccination pediatrician",
            r"\bkalendarz szczepień\b": "baby vaccination doctor",
            r"\bsuplement(y|ów|acja)\b": "baby vitamins supplements",
            r"\bwitamin(a|y) d\b": "baby vitamin d drops",
            r"\bmleko modyfikowane\b": "baby formula milk",
            r"\bpierwsza pomoc\b": "baby first aid",
            r"\bproblemy ze snem\b": "baby sleep problems",
            r"\bproblemy z zasypianiem\b": "baby bedtime routine",
            r"\bwychowanie\b": "parenting baby toddler",
            r"\bniemowl(a|ę|ęcia|ąt|ak|akiem)\b": "newborn baby infant",
            r"\bnoworo(dek|dk|dka|dkiem)\b": "newborn baby",
            r"\bbezpiecze[ńn](|stwo|stwa)\b": "baby safety home",
            r"\bdziecko\b": "child",
            r"\bdzieck(a|o|i|iem)\b": "child",
            r"\bdzieci\b": "children",
            r"\bmaluszu?k(a|i|iem)?\b": "baby",
            r"\bsen\b": "baby sleeping",
            r"\busypianie\b": "baby bedtime",
            r"\bokres snu\b": "baby sleep",
            r"\bodporno[sś](ć|ci)\b": "baby immunity health",
            r"\bkarmienie\b": "baby feeding",
            r"\bjedzenie\b": "baby food",
            r"\bdieta\b": "baby diet nutrition",
            r"\bposi(ł|l)ek\b": "baby meal",
            r"\brodzic(a|e|ów)?\b": "parent baby",
            r"\bopiek(a|ą|i)\b": "baby care parent",
            r"\brozw[oó]j(|u)\b": "child development",
            r"\bzabawki\b": "baby toys",
            r"\bporad(y|a)\b": "parenting advice",
            r"\bwskaz[oó]w?k(i|a)\b": "parenting tips",
            r"\bzdrowi(e|a|u)\b": "baby health pediatric",
            r"\bprzytulno[sś](ć|ci)\b": "baby comfort",
            r"\bjak\b": "how",
            r"\bco\b": "what",
            r"\bdla\b": "for",
        }
        s = q.lower()
        for pat, rep in mapping.items():
            try:
                s = re.sub(pat, rep, s, flags=re.IGNORECASE)
            except re.error:
                continue
        
        # Remove all Polish special characters
        polish_chars = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'a', 'Ć': 'c', 'Ę': 'e', 'Ł': 'l', 'Ń': 'n',
            'Ó': 'o', 'Ś': 's', 'Ź': 'z', 'Ż': 'z'
        }
        for pl, en in polish_chars.items():
            s = s.replace(pl, en)
        
        # Clean up non-ASCII and extra spaces
        s = re.sub(r"[^\w\s-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    
    def download_unsplash(query, per_page=4):
        """Download images from Unsplash using official API."""
        saved = []
        unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        
        if not unsplash_access_key:
            print("⚠️  Brak UNSPLASH_ACCESS_KEY w .env")
            return []
        
        eng_query = _translate_to_english(query)
        print(f"   Unsplash query: '{eng_query}'")
        
        try:
            api_url = 'https://api.unsplash.com/search/photos'
            params = {
                'query': eng_query,
                'per_page': per_page * 2,  # Get more to filter
                'orientation': 'landscape',
                'content_filter': 'high',
                'order_by': 'relevant'
            }
            api_headers = {
                'Authorization': f'Client-ID {unsplash_access_key}',
                'Accept-Version': 'v1'
            }
            
            r = requests.get(api_url, params=params, headers=api_headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            if not data.get('results'):
                print(f"   ⚠️  Unsplash: brak wyników dla '{eng_query}'")
                return []
            
            download_headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            for i, photo in enumerate(data.get('results', [])):
                if len(saved) >= per_page:
                    break
                
                img_url = photo['urls'].get('regular') or photo['urls'].get('full')
                download_url = photo.get('links', {}).get('download_location')
                if not img_url:
                    continue
                
                # Check description for relevance
                desc = (photo.get('description', '') or photo.get('alt_description', '')).lower()
                alt_desc = photo.get('alt_description', '').lower()
                
                # Skip obviously irrelevant images
                skip_keywords = ['tights', 'stockings', 'tower', 'building', 'architecture', 
                                'city', 'landscape', 'mountain', 'ocean', 'abstract', 'pattern',
                                'fashion', 'model', 'adult', 'sexy', 'lingerie']
                if any(kw in desc or kw in alt_desc for kw in skip_keywords):
                    print(f"   ⚠️  Pominięto: {desc[:50]}...")
                    continue
                
                ext = '.jpg'
                fn = f"img_unsplash_{len(saved)}{ext}"
                path = os.path.join(img_dir, fn)
                
                try:
                    img_r = requests.get(img_url, timeout=30, headers=download_headers)
                    img_r.raise_for_status()
                    with open(path, 'wb') as f:
                        f.write(img_r.content)
                    
                    if not _is_image_suitable(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                        continue
                    
                    meta = {
                        "provider": "Unsplash",
                        "photographer": photo['user']['name'],
                        "photographer_url": photo['user']['links']['html'],
                        "source_url": photo['links']['html'],
                        "license": "Unsplash License",
                        "license_url": "https://unsplash.com/license",
                        "description": photo.get('description') or photo.get('alt_description', ''),
                        "downloaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    meta_path = os.path.splitext(path)[0] + '.json'
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    
                    saved.append({
                        'filename': fn,
                        'description': meta['description'],
                        'photographer': meta['photographer']
                    })
                    rel_path = os.path.join('img', 'generated', slug, fn)
                    print(f"✓ Pobrano obraz (Unsplash): {rel_path}")
                    
                    # Trigger download endpoint for Unsplash API guidelines
                    if download_url:
                        try:
                            requests.get(download_url, headers=api_headers, timeout=5)
                        except Exception:
                            pass
                    
                    time.sleep(0.3)
                except Exception as e:
                    print(f"   ⚠️  Błąd pobierania {fn}: {e}")
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                    continue
            
            return saved
            
        except Exception as e:
            print(f"   ⚠️  Unsplash API error: {e}")
            return []
    
    def download_pexels(query, per_page=4):
        """Download images from Pexels with content filtering and metadata capture."""
        headers = {"Authorization": PEXELS_API_KEY}
        safe_query = _translate_to_english(query)
        
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
                url_lower = p.get('url', '').lower()
                
                # Expanded skip keywords for better filtering
                skip_keywords = [
                    'disaster', 'earthquake', 'accident', 'crying', 'sad',
                    'tights', 'stockings', 'legwear', 'pantyhose', 'hosiery',
                    'tower', 'electrical', 'power', 'transmission', 'pylon',
                    'building', 'architecture', 'city', 'urban', 'skyline',
                    'fashion', 'model', 'sexy', 'lingerie', 'adult',
                    'abstract', 'pattern', 'texture', 'background',
                    'mountain', 'landscape', 'ocean', 'beach', 'sunset'
                ]
                
                # Must have baby/child related keywords
                required_keywords = ['baby', 'infant', 'child', 'toddler', 'parent', 'mother', 
                                    'father', 'family', 'pediatric', 'newborn']
                has_required = any(kw in desc or kw in url_lower for kw in required_keywords)
                has_skip = any(kw in desc or kw in url_lower for kw in skip_keywords)
                
                if has_skip or not has_required:
                    if has_skip:
                        print(f"   ⚠️  Pominięto (Pexels): {desc[:50]}...")
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
                        
                    # Log downloaded image to console (relative path under site static/)
                    rel_path = os.path.join('img', 'generated', slug, fn)
                    print(f"✓ Pobrano obraz (Pexels): {rel_path}")

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

    # Try Unsplash FIRST (no API key needed)
    print("🔍 Szukam obrazów na Unsplash...")
    imgs = download_unsplash(topic, per_page=4)
    
    # If Unsplash fails and Pexels API key is available, try Pexels
    if not imgs and PEXELS_API_KEY:
        print("⚠️  Unsplash nie zwrócił obrazów, próbuję Pexels...")
        imgs = download_pexels(topic, per_page=4)
    elif not imgs and not PEXELS_API_KEY:
        print("⚠️  Unsplash nie zwrócił obrazów i brak klucza Pexels API")
    
    # Final message if still no images
    if not imgs:
        print("⚠️  Nie znaleziono obrazów. Rozważ dodanie PEXELS_API_KEY lub generowanie AI obrazów.")
    
    if imgs:
            # Attempt to upload downloaded images to S3 if credentials and bucket are configured.
            uploaded_map = {}
            s3_bucket = os.getenv('S3_BUCKET') or None
            # If .s3_migration_map.json provided bucket, use it
            try:
                if not s3_bucket:
                    s3_bucket = None
                    # Try to derive bucket from s3_base if it's a full URL like https://bucket.s3.region.amazonaws.com
                    if s3_base and s3_base.startswith('https://'):
                        # naive extraction
                        host = s3_base.split('://', 1)[1]
                        s3_bucket = host.split('.s3')[0]
            except Exception:
                s3_bucket = None

            do_upload = False
            s3_client = None
            if s3_bucket:
                try:
                    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
                    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                    aws_session_token = os.getenv('AWS_SESSION_TOKEN')
                    region_name = os.getenv('AWS_REGION') or None
                    # Pass credentials explicitly if present
                    if aws_access_key_id and aws_secret_access_key:
                        s3_client = boto3.client(
                            's3',
                            region_name=region_name,
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_session_token=aws_session_token
                        )
                        sts = boto3.client(
                            'sts',
                            region_name=region_name,
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_session_token=aws_session_token
                        )
                    else:
                        s3_client = boto3.client('s3', region_name=region_name)
                        sts = boto3.client('sts', region_name=region_name)
                    # Quick credentials check
                    sts.get_caller_identity()
                    do_upload = True
                except NoCredentialsError:
                    print('AWS credentials not found; skipping S3 upload.')
                    do_upload = False
                except Exception as e:
                    # any other error, skip upload but continue
                    print('S3 upload disabled (client error):', e)
                    do_upload = False

            for img in imgs:
                rel_path = os.path.join('img', 'generated', slug, img['filename'])
                local_file = os.path.join(img_dir, img['filename'])
                if do_upload and s3_client and s3_bucket:
                    key = rel_path.replace(os.path.sep, '/')
                    try:
                        content_type, _ = mimetypes.guess_type(local_file)
                        extra = {}
                        if content_type:
                            extra['ContentType'] = content_type
                        # default to public-read unless explicitly disabled
                        add_acl = os.getenv('S3_PUBLIC', 'true').lower() in ('1', 'true', 'yes')
                        if add_acl:
                            extra['ACL'] = 'public-read'
                        s3_client.upload_file(local_file, s3_bucket, key, ExtraArgs=extra)
                        s3_url = f"https://{s3_bucket}.s3.{os.getenv('AWS_REGION') or 'eu-north-1'}.amazonaws.com/{key}"
                        uploaded_map[rel_path] = s3_url
                        print(f"Uploaded to S3: {s3_url}")
                    except NoCredentialsError:
                        print('AWS credentials disappeared; skipping remaining uploads.')
                        do_upload = False
                    except ClientError as ce:
                        # Some buckets disallow ACLs; retry without ACL if that's the case
                        try:
                            err_code = ''
                            if hasattr(ce, 'response') and isinstance(ce.response, dict):
                                err_code = ce.response.get('Error', {}).get('Code', '')
                            if err_code == 'AccessControlListNotSupported' and add_acl:
                                # retry without ACL
                                try:
                                    extra.pop('ACL', None)
                                    s3_client.upload_file(local_file, s3_bucket, key, ExtraArgs=extra)
                                    s3_url = f"https://{s3_bucket}.s3.{os.getenv('AWS_REGION') or 'eu-north-1'}.amazonaws.com/{key}"
                                    uploaded_map[rel_path] = s3_url
                                    print(f"Uploaded to S3 (no ACL): {s3_url}")
                                    continue
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        print('S3 upload failed for', local_file, ce)
                    except Exception as e:
                        # Some upload helpers raise a wrapped exception (e.g., S3UploadFailedError)
                        # which may contain the underlying AccessControlListNotSupported message.
                        try:
                            msg = str(e)
                        except Exception:
                            msg = ''
                        if 'AccessControlListNotSupported' in msg and add_acl:
                            try:
                                extra.pop('ACL', None)
                                s3_client.upload_file(local_file, s3_bucket, key, ExtraArgs=extra)
                                s3_url = f"https://{s3_bucket}.s3.{os.getenv('AWS_REGION') or 'eu-north-1'}.amazonaws.com/{key}"
                                uploaded_map[rel_path] = s3_url
                                print(f"Uploaded to S3 (no ACL): {s3_url}")
                                continue
                            except Exception as e2:
                                print('Retry without ACL failed for', local_file, e2)
                                continue
                        print('Unexpected error uploading to S3 for', local_file, e)

            # Merge uploaded_map into s3_map and persist to .s3_migration_map.json if any uploads succeeded
            if uploaded_map:
                try:
                    s3_map.update(uploaded_map)
                    map_path = os.path.join(base, '.s3_migration_map.json')
                    out = {
                        'bucket': os.getenv('S3_BUCKET') or (s3_bucket or ''),
                        'region': os.getenv('AWS_REGION') or 'eu-north-1',
                        'uploaded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'mapping': s3_map
                    }
                    with open(map_path, 'w', encoding='utf-8') as mf:
                        json.dump(out, mf, ensure_ascii=False, indent=2)
                    print('Updated .s3_migration_map.json with uploads')
                except Exception as e:
                    print('Failed to update .s3_migration_map.json:', e)

            # Set featured image to first uploaded URL if present, otherwise fall back to existing map or local path
            local_path = f"/img/generated/{slug}/{imgs[0]['filename']}"
            featured_url = None
            
            # Only use S3 URLs if files were actually uploaded to S3
            s3_local_key = f"img/generated/{slug}/{imgs[0]['filename']}"
            if s3_local_key in s3_map:
                featured_url = s3_map.get(s3_local_key)
            elif uploaded_map:  # Only use s3_base if we just uploaded files
                if s3_base and s3_local_key in uploaded_map:
                    featured_url = s3_base.rstrip('/') + '/' + s3_local_key.lstrip('/')
            
            data['featured_image'] = featured_url or local_path

            # Replace [IMAGE-n] placeholders with actual images or add them in logical places
            body = data.get('body', '')
            for i, img in enumerate(imgs):
                placeholder = f"[IMAGE-{i+1}]"
                # regex to match Markdown image links that use IMAGE-n as the URL: ![alt](IMAGE-n)
                md_image_pattern = re.compile(r'!\[([^\]]*)\]\(IMAGE-' + str(i+1) + r'\)')

                def _sanitize_attr(s):
                    if not s:
                        return ""
                    v = str(s)
                    v = v.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
                    v = v.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                    v = ' '.join(v.split())
                    v = v.replace('"', '\\"')
                    return v

                alt_text = _sanitize_attr(img.get('description') or '')
                photographer = _sanitize_attr(img.get('photographer') or '')
                caption_text = _sanitize_attr((img.get('description') or '') + (f" (Photo: {img.get('photographer')})" if img.get('photographer') else ''))

                # Only use /img/generated/<slug>/img_0.jpeg, never /posts/<slug>/img/generated/...
                # Prefer S3-hosted image if actually uploaded, otherwise use local path
                rel_img_path = f"img/generated/{slug}/{img['filename']}"
                if rel_img_path in s3_map:
                    img_src = s3_map.get(rel_img_path)
                elif uploaded_map and rel_img_path in uploaded_map:  # Only if we just uploaded
                    if s3_base:
                        img_src = s3_base.rstrip('/') + '/' + rel_img_path.lstrip('/')
                    else:
                        img_src = "/" + rel_img_path
                else:
                    # Use local path with leading slash
                    img_src = "/" + rel_img_path

                img_md = (
                    "\n\n{{< figure src=\"" + img_src + "\" "
                    "alt=\"" + alt_text + "\" "
                    "caption=\"" + caption_text + "\" "
                    "class=\"article-image\" >}}\n\n"
                )

                # Prefer explicit placeholder replacement [IMAGE-n]
                if placeholder in body:
                    body = body.replace(placeholder, img_md)
                # Also replace Markdown image links that were written as ![alt](IMAGE-n)
                elif md_image_pattern.search(body):
                    body = md_image_pattern.sub(img_md, body)
                elif i == 0:
                    body = img_md + body
                else:
                    parts = body.split("\n\n")
                    if len(parts) > i+1:
                        parts.insert(i+1, img_md)
                        body = "\n\n".join(parts)
            # Deduplicate repeated figure shortcodes that reference the same image
            # Sometimes the AI output already contains images and our insertion can create duplicates.
            seen_srcs = set()
            def _dedup_figure(m):
                tag = m.group(0)
                src_m = re.search(r'src=\"([^\"]+)\"', tag)
                if not src_m:
                    return tag
                src = src_m.group(1)
                if src in seen_srcs:
                    # remove duplicate occurrence
                    return ''
                seen_srcs.add(src)
                return tag

            body = re.sub(r'\{\{<\s*figure\b[^>]*>\s*\}\}', _dedup_figure, body)
            data['body'] = body

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
    
    # Add bibliography if research was used
    if data.get('has_research') and data.get('research'):
        print("📚 Dodaję bibliografię do artykułu...")
        research_mgr = ScientificResearchManager()
        bibliography = research_mgr.generate_bibliography(data['research'])
        data['body'] = data['body'] + bibliography

    md = make_markdown_file(data)
    print("Saved:", md)
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        git_commit_and_push(md, f"Automated: {data.get('title')}")
