#!/usr/bin/env python3
import re
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class SEOHelper:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.posts_dir = os.path.join(base_dir, "content", "posts")
        self._load_keyword_data()
        
    def _load_keyword_data(self):
        """Load keyword research data for better SEO."""
        self.keyword_clusters = {
            "rozwój dziecka": [
                "rozwój niemowlaka",
                "kamienie milowe",
                "kiedy dziecko siada",
                "kiedy dziecko chodzi",
                "rozwój mowy"
            ],
            "karmienie": [
                "rozszerzanie diety",
                "blw",
                "karmienie piersią",
                "mleko modyfikowane",
                "posiłki dla niemowlaka"
            ],
            "zdrowie": [
                "odporność dziecka",
                "choroba u dziecka",
                "szczepienia",
                "gorączka",
                "kolka"
            ]
        }
        
    def analyze_content(self, content: str) -> Dict:
        """Analyze content and suggest SEO improvements."""
        word_count = len(content.split())
        paragraphs = content.split('\n\n')
        headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
        
        return {
            "word_count": word_count,
            "paragraph_count": len(paragraphs),
            "heading_count": len(headings),
            "suggestions": self._generate_suggestions(content, headings)
        }
    
    def _generate_suggestions(self, content: str, headings: List[str]) -> List[str]:
        """Generate SEO improvement suggestions."""
        suggestions = []
        
        if len(headings) < 3:
            suggestions.append("Add more headings (H2, H3) to improve structure")
            
        # Check keyword density
        words = content.lower().split()
        for cluster, related in self.keyword_clusters.items():
            count = sum(1 for w in words if any(kw in w for kw in [cluster] + related))
            density = count / len(words) * 100
            if density < 1:
                suggestions.append(f"Increase usage of '{cluster}' related keywords")
            elif density > 5:
                suggestions.append(f"Reduce keyword density for '{cluster}'")
                
        # Check content length
        if len(words) < 800:
            suggestions.append("Content might be too short for good SEO")
        
        return suggestions
    
    def get_internal_linking_suggestions(self, content: str, current_slug: str) -> List[Dict]:
        """Find relevant internal linking opportunities."""
        links = []
        try:
            # Find related posts
            for entry in os.scandir(self.posts_dir):
                if not entry.name.endswith('.md') or entry.name.startswith(current_slug):
                    continue
                    
                with open(entry.path, 'r', encoding='utf-8') as f:
                    post_content = f.read()
                    
                # Extract front matter
                if '---' in post_content:
                    parts = post_content.split('---', 2)
                    if len(parts) >= 3:
                        try:
                            # Parse front matter
                            front_matter = parts[1].strip()
                            for line in front_matter.split('\n'):
                                if line.startswith('title:'):
                                    title = line.split(':', 1)[1].strip().strip('"\'')
                                    
                                    # Check content relevance
                                    relevance = self._calculate_relevance(content, post_content)
                                    if relevance > 0.3:  # Threshold for relevance
                                        links.append({
                                            "title": title,
                                            "file": entry.name,
                                            "relevance": relevance
                                        })
                        except Exception:
                            continue
                            
        except Exception as e:
            print(f"Error finding internal links: {e}")
            
        return sorted(links, key=lambda x: x['relevance'], reverse=True)[:5]
    
    def _calculate_relevance(self, source: str, target: str) -> float:
        """Calculate content relevance score."""
        # Simple relevance calculation based on shared keywords
        source_words = set(w.lower() for w in re.findall(r'\w+', source))
        target_words = set(w.lower() for w in re.findall(r'\w+', target))
        
        # Get important keywords (longer words are usually more meaningful)
        source_keywords = {w for w in source_words if len(w) > 5}
        target_keywords = {w for w in target_words if len(w) > 5}
        
        if not source_keywords or not target_keywords:
            return 0
            
        shared = len(source_keywords.intersection(target_keywords))
        return shared / len(source_keywords.union(target_keywords))
    
    def generate_meta_tags(self, title: str, summary: str) -> Dict[str, str]:
        """Generate SEO meta tags."""
        # Clean and truncate
        clean_title = re.sub(r'["\']', '', title)
        clean_summary = re.sub(r'["\']', '', summary)
        
        return {
            "title": clean_title[:60],
            "description": clean_summary[:160],
            "og:title": clean_title[:90],
            "og:description": clean_summary[:200],
            "twitter:title": clean_title[:70],
            "twitter:description": clean_summary[:200]
        }
        
    def generate_structured_data(self, data: Dict) -> Dict:
        """Generate JSON-LD structured data for article."""
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": data.get('title', '')[:110],
            "description": data.get('summary', ''),
            "image": data.get('featured_image', ''),
            "author": {
                "@type": "Person",
                "name": "Automated AI"
            },
            "datePublished": datetime.now().isoformat(),
            "dateModified": datetime.now().isoformat(),
            "publisher": {
                "@type": "Organization",
                "name": "Poradnik Rodzica",
                "logo": {
                    "@type": "ImageObject",
                    "url": "/img/logo.png"  # Update with your actual logo path
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"https://example.org/posts/{data.get('slug', '')}"
            },
            "keywords": ",".join(data.get('tags', [])),
            "articleSection": ",".join(data.get('categories', []))
        }