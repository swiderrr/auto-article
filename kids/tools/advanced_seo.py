#!/usr/bin/env python3
import re
import json
import os
from datetime import datetime, timezone
import html
from urllib.parse import quote
from typing import List, Dict, Optional
import requests

class AdvancedSEOHelper:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.posts_dir = os.path.join(base_dir, "content", "posts")
        self.load_data()
        
    def load_data(self):
        """Load SEO research data."""
        self.keyword_data = {
            "parenting": {
                "primary_keywords": [
                    "rozwój dziecka",
                    "wychowanie dzieci",
                    "opieka nad dzieckiem"
                ],
                "lsi_keywords": [  # Latent Semantic Indexing keywords
                    "jak wychowywać",
                    "rozwój niemowlaka",
                    "problemy wychowawcze"
                ],
                "questions": [
                    "jak pomóc dziecku w rozwoju",
                    "kiedy dziecko powinno",
                    "co robić gdy dziecko"
                ]
            },
            "health": {
                "primary_keywords": [
                    "zdrowie dziecka",
                    "choroba dziecka",
                    "odporność dzieci"
                ],
                "lsi_keywords": [
                    "naturalne sposoby",
                    "domowe sposoby",
                    "profilaktyka"
                ],
                "questions": [
                    "jak wzmocnić odporność",
                    "co podać dziecku na",
                    "kiedy do lekarza"
                ]
            }
        }
        
        # Load topic clusters for better content organization
        self.topic_clusters = {
            "rozwój": [
                "rozwój fizyczny",
                "rozwój poznawczy",
                "rozwój emocjonalny",
                "rozwój społeczny",
                "kamienie milowe"
            ],
            "żywienie": [
                "karmienie piersią",
                "rozszerzanie diety",
                "alergeny",
                "przepisy",
                "harmonogram posiłków"
            ]
        }
        
    def optimize_title(self, title: str, keywords: List[str]) -> str:
        """Create an SEO-optimized title."""
        # Ensure main keyword is at the beginning
        for kw in keywords:
            if kw.lower() in title.lower():
                if not title.lower().startswith(kw.lower()):
                    # Move keyword to start if possible
                    title = f"{kw.capitalize()} - {title}"
                break
                
        # Add power words if missing
        power_words = ["najlepszy", "kompletny", "skuteczny", "sprawdzony"]
        if not any(w in title.lower() for w in power_words):
            title = f"{title} - {power_words[0]} poradnik"
            
        # Truncate to optimal length (55-60 chars)
        if len(title) > 60:
            title = title[:57] + "..."
            
        return title
        
    def generate_meta_description(self, content: str, keywords: List[str]) -> str:
        """Generate an optimized meta description."""
        # Extract first paragraph or summary
        first_para = re.search(r'\n\n(.*?)\n\n', content)
        desc = first_para.group(1) if first_para else content[:200]
        
        # Clean up and ensure it has keywords
        desc = re.sub(r'\s+', ' ', desc).strip()
        desc = html.escape(desc)
        
        # Add call to action if missing
        ctas = ["Dowiedz się więcej!", "Sprawdź jak!", "Zobacz pełny poradnik!"]
        if not any(cta in desc for cta in ctas):
            desc = f"{desc} {ctas[0]}"
            
        # Ensure optimal length
        if len(desc) > 155:
            desc = desc[:152] + "..."
            
        return desc
        
    def generate_structured_data(self, data: Dict) -> Dict:
        """Generate comprehensive Schema.org structured data."""
        base_data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": data.get('title', '')[:110],
            "description": data.get('summary', ''),
            "image": data.get('featured_image', ''),
            "author": {
                "@type": "Person",
                "name": "Automated AI"
            },
            "publisher": {
                "@type": "Organization",
                "name": "Poradnik Rodzica",
                "logo": {
                    "@type": "ImageObject",
                    "url": "/img/logo.png"
                }
            },
            "datePublished": datetime.now(timezone.utc).isoformat(),
                "dateModified": datetime.now(timezone.utc).isoformat(),
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"https://example.org/posts/{data.get('slug', '')}"
            },
            "keywords": ",".join(data.get('tags', [])),
            "articleSection": ",".join(data.get('categories', []))
        }
        
        # Add FAQ if content has Q&A format
        questions = re.findall(r'###\s+([^#\n]+)\?', data.get('body', ''))
        if questions:
            base_data["@type"] = "FAQPage"
            base_data["mainEntity"] = []
            for q in questions:
                # Use re.escape for the question text and a raw regex to capture the answer block
                pattern = re.escape(q) + r'\?(.*?)(?:###|$)'
                answer = re.search(pattern, data.get('body', ''), re.DOTALL)
                if answer:
                    base_data["mainEntity"].append({
                        "@type": "Question",
                        "name": f"{q}?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer.group(1).strip()
                        }
                    })

        return base_data

    def generate_meta_tags(self, title: str, summary: str) -> Dict[str, str]:
        """Compatibility wrapper to generate basic meta tags (title, description, OG, Twitter)."""
        # Clean and truncate
        clean_title = re.sub(r'["\']', '', title)[:60]
        clean_summary = re.sub(r'["\']', '', summary)[:160]

        # Use existing helpers to further optimize
        optimized_title = self.optimize_title(clean_title, [])
        optimized_description = self.generate_meta_description(clean_summary, [])

        return {
            "title": optimized_title,
            "description": optimized_description,
            "og:title": optimized_title[:90],
            "og:description": optimized_description[:200],
            "twitter:title": optimized_title[:70],
            "twitter:description": optimized_description[:200]
        }

    def analyze_content(self, content: str) -> Dict:
        """Analyze content and provide simple SEO suggestions (compatible interface)."""
        word_count = len(content.split()) if content else 0
        paragraphs = content.split('\n\n') if content else []
        headings = re.findall(r'^#{1,3}\s+(.+)$', content or '', re.MULTILINE)

        suggestions = []
        if len(headings) < 3:
            suggestions.append("Add more headings (H2, H3) to improve structure")
        if word_count < 800:
            suggestions.append("Content might be too short for good SEO")

        return {
            "word_count": word_count,
            "paragraph_count": len(paragraphs),
            "heading_count": len(headings),
            "suggestions": suggestions
        }

    def get_internal_linking_suggestions(self, content: str, current_slug: str) -> List[Dict]:
        """Compatibility wrapper that calls suggest_internal_links."""
        return self.suggest_internal_links(content, current_slug)
        
    def optimize_headers(self, content: str) -> str:
        """Optimize header structure for SEO."""
        lines = content.split('\n')
        toc = []
        current_h2 = None
        
        for i, line in enumerate(lines):
            if line.startswith('## '):
                current_h2 = line[3:].strip()
                toc.append(f"- [{current_h2}](#{quote(current_h2.lower().replace(' ', '-'))})")
            elif line.startswith('### '):
                if current_h2:
                    toc.append(f"  - [{line[4:].strip()}](#{quote(line[4:].strip().lower().replace(' ', '-'))})")
                    
        if toc:
            toc_text = "## Spis treści\n\n" + "\n".join(toc) + "\n\n"
            # Insert after first paragraph
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 0:
                    lines.insert(i+1, toc_text)
                    break
                    
        return '\n'.join(lines)
        
    def suggest_internal_links(self, content: str, current_slug: str) -> List[Dict]:
        """Find and suggest relevant internal links."""
        links = []
        try:
            for entry in os.scandir(self.posts_dir):
                if not entry.name.endswith('.md') or entry.name.startswith(current_slug):
                    continue
                    
                with open(entry.path, 'r', encoding='utf-8') as f:
                    post = f.read()
                    relevance = self._calculate_relevance(content, post)
                    if relevance > 0.3:
                        # Extract title from frontmatter
                        title_match = re.search(r'title:\s*"([^"]+)"', post)
                        if title_match:
                            links.append({
                                'title': title_match.group(1),
                                'file': entry.name,
                                'relevance': relevance
                            })
        except Exception as e:
            print(f"Error suggesting internal links: {e}")
            
        return sorted(links, key=lambda x: x['relevance'], reverse=True)[:5]
        
    def _calculate_relevance(self, source: str, target: str) -> float:
        """Calculate content relevance using TF-IDF-like approach."""
        def get_keywords(text):
            words = re.findall(r'\b\w{4,}\b', text.lower())
            return set(w for w in words if len(w) > 4)
            
        source_kw = get_keywords(source)
        target_kw = get_keywords(target)
        
        if not source_kw or not target_kw:
            return 0
            
        common = source_kw.intersection(target_kw)
        return len(common) / (len(source_kw) + len(target_kw) - len(common))
        
    def generate_social_meta(self, data: Dict) -> Dict:
        """Generate social media meta tags."""
        title = data.get('title', '')
        desc = data.get('summary', '')
        image = data.get('featured_image', '')
        
        return {
            'og:title': title[:90],
            'og:description': desc[:200],
            'og:image': image,
            'og:type': 'article',
            'twitter:card': 'summary_large_image',
            'twitter:title': title[:70],
            'twitter:description': desc[:200],
            'twitter:image': image
        }
        
    def generate_image_meta(self, image_path: str, alt_text: str) -> Dict:
        """Generate image metadata including Schema.org ImageObject."""
        return {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "contentUrl": image_path,
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "acquireLicensePage": "https://example.org/license",
            "creditText": "Via Pexels",
            "creator": {
                "@type": "Organization",
                "name": "Pexels"
            },
            "copyrightNotice": "Image may be subject to copyright"
        }