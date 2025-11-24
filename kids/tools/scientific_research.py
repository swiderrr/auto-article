#!/usr/bin/env python3
"""
Scientific Research Integration for Article Generation
This module handles finding, verifying, and citing scientific research in articles.
Supports: PubMed, CrossRef, Semantic Scholar APIs
"""
import os
import json
import re
import time
import requests
from typing import List, Dict, Optional
from openai import OpenAI

class ScientificResearchManager:
    """Manages scientific research citations and verification for articles."""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize the research manager with OpenAI API key."""
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        # API endpoints for scientific databases
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.crossref_base = "https://api.crossref.org/works"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.europepmc_base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        self.core_base = "https://api.core.ac.uk/v3"
    
    def search_pubmed(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search PubMed database for scientific articles."""
        try:
            # Step 1: Search for article IDs
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'json',
                'sort': 'relevance'
            }
            
            response = requests.get(search_url, params=search_params, timeout=10)
            response.raise_for_status()
            search_data = response.json()
            
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                return []
            
            # Step 2: Fetch article details
            time.sleep(0.4)  # NCBI rate limit: 3 requests per second
            fetch_url = f"{self.pubmed_base}/esummary.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'json'
            }
            
            response = requests.get(fetch_url, params=fetch_params, timeout=10)
            response.raise_for_status()
            fetch_data = response.json()
            
            results = []
            for pmid in id_list:
                article = fetch_data.get('result', {}).get(pmid, {})
                if not article:
                    continue
                
                authors = []
                for author in article.get('authors', [])[:3]:  # First 3 authors
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
                
                if len(article.get('authors', [])) > 3:
                    authors.append('et al.')
                
                results.append({
                    'title': article.get('title', ''),
                    'authors': authors,
                    'year': article.get('pubdate', '').split()[0] if article.get('pubdate') else 'N/A',
                    'journal': article.get('source', ''),
                    'pmid': pmid,
                    'doi': article.get('elocationid', '').replace('doi: ', '') if 'doi' in article.get('elocationid', '').lower() else '',
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    'database': 'PubMed'
                })
            
            return results
            
        except Exception as e:
            print(f"✗ PubMed search error: {e}")
            return []
    
    def search_crossref(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search CrossRef database for scientific articles."""
        try:
            url = f"{self.crossref_base}"
            params = {
                'query': query,
                'rows': max_results,
                'sort': 'relevance',
                'select': 'DOI,title,author,published,container-title,abstract'
            }
            
            headers = {
                'User-Agent': 'ScientificResearchBot/1.0 (mailto:research@example.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('message', {}).get('items', []):
                authors = []
                for author in item.get('author', [])[:3]:
                    family = author.get('family', '')
                    given = author.get('given', '')
                    if family:
                        name = f"{family}, {given[0]}." if given else family
                        authors.append(name)
                
                if len(item.get('author', [])) > 3:
                    authors.append('et al.')
                
                # Extract year from published date
                year = 'N/A'
                pub_date = item.get('published', {}).get('date-parts', [[]])[0]
                if pub_date:
                    year = str(pub_date[0])
                
                title = item.get('title', [''])[0] if isinstance(item.get('title'), list) else item.get('title', '')
                
                results.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'journal': item.get('container-title', [''])[0] if isinstance(item.get('container-title'), list) else item.get('container-title', ''),
                    'doi': item.get('DOI', ''),
                    'url': f"https://doi.org/{item.get('DOI', '')}" if item.get('DOI') else '',
                    'database': 'CrossRef'
                })
            
            return results
            
        except Exception as e:
            print(f"✗ CrossRef search error: {e}")
            return []
    
    def search_semantic_scholar(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search Semantic Scholar database for scientific articles."""
        try:
            url = f"{self.semantic_scholar_base}/paper/search"
            params = {
                'query': query,
                'limit': max_results,
                'fields': 'title,authors,year,venue,externalIds,abstract,url'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for paper in data.get('data', []):
                authors = []
                for author in paper.get('authors', [])[:3]:
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
                
                if len(paper.get('authors', [])) > 3:
                    authors.append('et al.')
                
                external_ids = paper.get('externalIds', {})
                doi = external_ids.get('DOI', '')
                pmid = external_ids.get('PubMed', '')
                
                url = paper.get('url', '')
                if not url and doi:
                    url = f"https://doi.org/{doi}"
                elif not url and pmid:
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                
                results.append({
                    'title': paper.get('title', ''),
                    'authors': authors,
                    'year': str(paper.get('year', 'N/A')),
                    'journal': paper.get('venue', ''),
                    'doi': doi,
                    'pmid': pmid,
                    'url': url,
                    'database': 'Semantic Scholar'
                })
            
            return results
            
        except Exception as e:
            print(f"✗ Semantic Scholar search error: {e}")
            return []
    
    def search_europepmc(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search Europe PMC database for biomedical and life sciences literature."""
        try:
            url = f"{self.europepmc_base}/search"
            params = {
                'query': query,
                'format': 'json',
                'pageSize': max_results,
                'sort': 'RELEVANCE'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('resultList', {}).get('result', []):
                authors = []
                author_str = item.get('authorString', '')
                if author_str:
                    # Parse author string (usually "Smith J, Doe A, et al.")
                    author_parts = author_str.split(',')
                    authors = [a.strip() for a in author_parts[:3]]
                    if len(author_parts) > 3:
                        authors.append('et al.')
                
                results.append({
                    'title': item.get('title', ''),
                    'authors': authors,
                    'year': str(item.get('pubYear', 'N/A')),
                    'journal': item.get('journalTitle', ''),
                    'doi': item.get('doi', ''),
                    'pmid': item.get('pmid', ''),
                    'url': f"https://europepmc.org/article/MED/{item.get('pmid')}" if item.get('pmid') else '',
                    'database': 'Europe PMC',
                    'abstract': item.get('abstractText', '')[:200] if item.get('abstractText') else ''
                })
            
            return results
            
        except Exception as e:
            print(f"✗ Europe PMC search error: {e}")
            return []
    
    def search_all_databases(self, topic: str, count_per_db: int = 3) -> List[Dict[str, str]]:
        """Search all available scientific databases with medical focus and combine results."""
        all_results = []
        
        # Add medical/pediatric keywords to improve relevance
        medical_keywords = ['infant', 'child', 'pediatric', 'baby', 'parenting', 'maternal', 'health']
        is_medical_topic = any(kw in topic.lower() for kw in medical_keywords)
        
        print("  📚 Przeszukuję PubMed (priorytet medyczny)...")
        pubmed_results = self.search_pubmed(topic, max_results=count_per_db * 2)  # Get more from PubMed
        all_results.extend(pubmed_results)
        print(f"     Znaleziono: {len(pubmed_results)} artykułów")
        
        time.sleep(0.5)  # Rate limiting
        
        print("  📚 Przeszukuję Europe PMC (medycyna i nauki biologiczne)...")
        europepmc_results = self.search_europepmc(topic, max_results=count_per_db)
        all_results.extend(europepmc_results)
        print(f"     Znaleziono: {len(europepmc_results)} artykułów")
        
        time.sleep(0.5)  # Rate limiting
        
        # Only search general databases if medical databases yielded few results
        if len(all_results) < 3:
            print("  📚 Przeszukuję CrossRef...")
            # Add medical filter to CrossRef query
            crossref_query = f"{topic} (pediatric OR infant OR child OR health OR medical)"
            crossref_results = self.search_crossref(crossref_query, max_results=count_per_db)
            all_results.extend(crossref_results)
            print(f"     Znaleziono: {len(crossref_results)} artykułów")
            
            time.sleep(0.5)  # Rate limiting
            
            print("  📚 Przeszukuję Semantic Scholar...")
            semantic_results = self.search_semantic_scholar(topic, max_results=count_per_db)
            all_results.extend(semantic_results)
            print(f"     Znaleziono: {len(semantic_results)} artykułów")
        
        # Remove duplicates and filter for relevance
        seen = set()
        unique_results = []
        
        # Keywords that indicate relevant pediatric/parenting research
        relevant_keywords = [
            'infant', 'baby', 'child', 'pediatric', 'paediatric', 'newborn', 'neonatal',
            'parent', 'mother', 'father', 'maternal', 'pregnancy', 'breastfeeding',
            'vaccination', 'immunization', 'development', 'growth', 'nutrition',
            'sleep', 'feeding', 'health', 'care', 'toddler'
        ]
        
        # Keywords that indicate irrelevant research
        irrelevant_keywords = [
            'poetry', 'literature', 'writer', 'novel', 'poet', 'drama', 'theatre',
            'painting', 'sculpture', 'music composition', 'philosophy', 'theology',
            'calendar of life and work', 'biographical calendar', 'literary criticism'
        ]
        
        for paper in all_results:
            identifier = paper.get('doi') or paper.get('title', '').lower().strip()
            if identifier and identifier not in seen:
                # Check relevance
                title_lower = paper.get('title', '').lower()
                journal_lower = paper.get('journal', '').lower()
                combined_text = f"{title_lower} {journal_lower}"
                
                # Skip if irrelevant
                if any(kw in combined_text for kw in irrelevant_keywords):
                    print(f"     ⚠️  Pominięto nieistotne źródło: {paper.get('title', '')[:60]}...")
                    continue
                
                # Check if it has relevant keywords for pediatric/parenting topics
                has_relevant = any(kw in combined_text for kw in relevant_keywords)
                
                # Accept medical journals even without exact keywords
                medical_journals = ['pediatr', 'child', 'infant', 'obstetric', 'maternal', 'neonat', 'bmj', 'lancet', 'jama']
                is_medical_journal = any(mj in journal_lower for mj in medical_journals)
                
                if has_relevant or is_medical_journal:
                    seen.add(identifier)
                    unique_results.append(paper)
                else:
                    print(f"     ⚠️  Pominięto mało istotne źródło: {paper.get('title', '')[:60]}...")
        
        return unique_results
    
    def search_research(self, topic: str, count: int = 5) -> List[Dict[str, str]]:
        """
        Search for scientific research related to a topic using real databases.
        Tries Polish first, then English. Returns empty list if no results found.
        
        Args:
            topic: The topic to search for
            count: Number of research papers to find
            
        Returns:
            List of research paper information dicts, or empty list if no research found
        """
        # First, try real scientific databases with original query (Polish)
        print("🔍 Przeszukuję bazy danych naukowych (PL)...")
        results = self.search_all_databases(topic, count_per_db=2)
        
        # If no results in Polish, try English translation
        if not results:
            print("⚠️  Brak wyników po polsku, próbuję angielskiego...")
            english_topic = self._translate_topic_to_english(topic)
            if english_topic and english_topic.lower() != topic.lower():
                print(f"   Szukam: '{english_topic}'")
                results = self.search_all_databases(english_topic, count_per_db=2)
        
        if results:
            # If we have AI available, generate summaries for papers without them
            if self.client:
                print("  🤖 Generuję streszczenia badań...")
                for paper in results:
                    if 'summary' not in paper or not paper['summary']:
                        summary = self._generate_summary_for_paper(paper)
                        paper['summary'] = summary
            
            return results[:count]
        
        # No results found - return empty list to prevent article generation
        print("❌ Nie znaleziono żadnych badań naukowych dla tego tematu.")
        print("   Artykuł nie zostanie wygenerowany bez źródeł naukowych.")
        return []
    
    def _translate_topic_to_english(self, topic: str) -> str:
        """Translate Polish topic to English for better database search results."""
        if not self.client:
            # Simple fallback translations
            common_translations = {
                'niemowlę': 'infant',
                'niemowlęta': 'infants',
                'niemowlak': 'baby',
                'dziecko': 'child',
                'dzieci': 'children',
                'karmienie piersią': 'breastfeeding',
                'sen': 'sleep',
                'szczepienia': 'vaccination',
                'rozwój': 'development',
                'zdrowie': 'health',
                'bezpieczeństwo': 'safety',
                'dieta': 'diet',
                'odporność': 'immunity'
            }
            topic_lower = topic.lower()
            for pl, en in common_translations.items():
                topic_lower = topic_lower.replace(pl, en)
            return topic_lower
        
        try:
            prompt = f"""Przetłumacz ten temat z języka polskiego na angielski (zachowaj kontekst naukowy):

Temat PL: {topic}

Zwróć tylko przetłumaczony tekst, bez dodatkowych komentarzy."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś tłumaczem terminologii naukowej."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"    ⚠️  Błąd tłumaczenia: {e}")
            return topic
    
    def _generate_summary_for_paper(self, paper: Dict[str, str]) -> str:
        """Generate a Polish summary for a research paper using AI."""
        if not self.client:
            return "Brak dostępnego streszczenia."
        
        try:
            prompt = f"""Wygeneruj krótkie (1-2 zdania) streszczenie po polsku dla tego badania naukowego:

Tytuł: {paper.get('title', 'N/A')}
Autorzy: {', '.join(paper.get('authors', []))}
Czasopismo: {paper.get('journal', 'N/A')}
Rok: {paper.get('year', 'N/A')}

Streszczenie powinno opisywać główne wnioski i praktyczne zastosowanie badania w kontekście rodzicielstwa i opieki nad dziećmi."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem w streszczaniu badań naukowych dla rodziców."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"    ⚠️  Nie udało się wygenerować streszczenia: {e}")
            return "Brak dostępnego streszczenia."
    
    def _ai_search_fallback(self, topic: str, count: int = 5) -> List[Dict[str, str]]:
        """Fallback AI-based search when databases fail."""
        if not self.client:
            print("⚠️  OpenAI API key not configured")
            return []
        
        prompt = f"""Znajdź {count} rzeczywistych, istniejących badań naukowych lub artykułów naukowych związanych z tematem: "{topic}".

Dla każdego badania podaj:
1. Tytuł badania/artykułu (w języku oryginalnym)
2. Autorów (nazwiska i inicjały)
3. Rok publikacji
4. Czasopismo/źródło publikacji
5. DOI lub link do publikacji (jeśli dostępny)
6. Krótkie (1-2 zdania) streszczenie głównych wniosków po polsku

WAŻNE: Podaj TYLKO prawdziwe, istniejące badania. Nie wymyślaj tytułów ani autorów.
Zwróć odpowiedź w formacie JSON:

[
  {{
    "title": "tytuł badania",
    "authors": ["Nazwisko A.", "Nazwisko B."],
    "year": 2023,
    "journal": "nazwa czasopisma",
    "doi": "10.xxxx/xxxxx",
    "url": "https://...",
    "summary": "Krótkie streszczenie wniosków po polsku",
    "database": "AI Search"
  }},
  ...
]
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem w wyszukiwaniu i weryfikacji badań naukowych. Zawsze podajesz prawdziwe, istniejące źródła."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            text = response.choices[0].message.content
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                research_list = json.loads(json_match.group(0))
                return research_list
            else:
                print("⚠️  Nie znaleziono JSON w odpowiedzi AI")
                return []
                
        except Exception as e:
            print(f"✗ Błąd wyszukiwania badań: {e}")
            return []
    
    def verify_research(self, research: Dict[str, str]) -> Dict[str, any]:
        """
        Verify if a research paper actually exists using AI.
        
        Args:
            research: Dict with research paper information
            
        Returns:
            Dict with verification result and confidence score
        """
        if not self.client:
            return {"verified": False, "confidence": 0, "reason": "No API key"}
        
        prompt = f"""Zweryfikuj czy to badanie naukowe rzeczywiście istnieje:

Tytuł: {research.get('title', 'N/A')}
Autorzy: {', '.join(research.get('authors', []))}
Rok: {research.get('year', 'N/A')}
Czasopismo: {research.get('journal', 'N/A')}
DOI: {research.get('doi', 'N/A')}

Oceń na skali 0-100 jak bardzo jesteś pewien, że to badanie istnieje.
Zwróć odpowiedź w formacie JSON:

{{
  "exists": true/false,
  "confidence": 0-100,
  "reasoning": "krótkie uzasadnienie",
  "alternative_source": "jeśli znasz lepsze źródło dla tego tematu, podaj je tutaj"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem w weryfikacji autentyczności badań naukowych. Jesteś bardzo ostrożny i sceptyczny wobec potencjalnie fałszywych cytowań."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                return {"verified": False, "confidence": 0, "reason": "No JSON in response"}
                
        except Exception as e:
            print(f"✗ Błąd weryfikacji: {e}")
            return {"verified": False, "confidence": 0, "reason": str(e)}
    
    def generate_bibliography(self, research_list: List[Dict[str, str]]) -> str:
        """
        Generate a formatted bibliography section from research papers.
        
        Args:
            research_list: List of research paper dicts
            
        Returns:
            Markdown formatted bibliography
        """
        if not research_list:
            return ""
        
        bibliography = "\n\n## Bibliografia\n\n"
        bibliography += "*Artykuł oparty na następujących źródłach naukowych:*\n\n"
        
        for i, paper in enumerate(research_list, 1):
            authors = ", ".join(paper.get('authors', ['Autor nieznany']))
            title = paper.get('title', 'Tytuł niedostępny')
            year = paper.get('year', 'b.d.')
            journal = paper.get('journal', '')
            doi = paper.get('doi', '')
            url = paper.get('url', '')
            
            # Format citation
            citation = f"{i}. {authors} ({year}). *{title}*"
            
            if journal:
                citation += f". {journal}"
            
            if doi:
                citation += f". DOI: [{doi}](https://doi.org/{doi})"
            elif url:
                citation += f". [Link do publikacji]({url})"
            
            bibliography += citation + "\n\n"
        
        return bibliography
    
    def integrate_research_into_article(self, article_body: str, 
                                       research_list: List[Dict[str, str]]) -> str:
        """
        Integrate research citations into article body.
        
        Args:
            article_body: The article content
            research_list: List of research papers to cite
            
        Returns:
            Article body with citation markers [1], [2], etc.
        """
        # This is a simple integration - in practice, you'd want more sophisticated
        # placement of citations based on content relevance
        
        # For now, just add citation markers at the end of main paragraphs
        paragraphs = article_body.split('\n\n')
        
        # Add citations to substantial paragraphs (skip headers, images, etc.)
        citation_idx = 0
        for i, para in enumerate(paragraphs):
            # Skip markdown headings and shortcodes
            if para.startswith('#') or '{{<' in para or len(para) < 100:
                continue
            
            # Add citation at end of paragraph
            if citation_idx < len(research_list):
                # Add citation marker
                paragraphs[i] = para.rstrip() + f" [{citation_idx + 1}]"
                citation_idx += 1
        
        return '\n\n'.join(paragraphs)


def main():
    """CLI for testing research manager."""
    import sys
    
    if len(sys.argv) < 2:
        print("Scientific Research Manager")
        print("=" * 50)
        print("\nUsage:")
        print("  python scientific_research.py search '<topic>'")
        print("  python scientific_research.py verify '<research_json>'")
        return
    
    command = sys.argv[1].lower()
    manager = ScientificResearchManager()
    
    if command == "search" and len(sys.argv) >= 3:
        topic = sys.argv[2]
        print(f"\nSzukam badań na temat: {topic}\n")
        research = manager.search_research(topic, count=3)
        
        print(f"✓ Znaleziono {len(research)} badań:\n")
        for i, paper in enumerate(research, 1):
            print(f"{i}. {paper.get('title', 'N/A')}")
            print(f"   Autorzy: {', '.join(paper.get('authors', []))}")
            print(f"   Rok: {paper.get('year', 'N/A')}")
            print(f"   Źródło: {paper.get('journal', 'N/A')}")
            print(f"   Baza danych: {paper.get('database', 'N/A')}")
            print(f"   DOI: {paper.get('doi', 'N/A')}")
            print(f"   PMID: {paper.get('pmid', 'N/A')}")
            print(f"   URL: {paper.get('url', 'N/A')}")
            print(f"   Podsumowanie: {paper.get('summary', 'N/A')}")
            print()
        
        # Save to file
        with open('research_output.json', 'w', encoding='utf-8') as f:
            json.dump(research, f, ensure_ascii=False, indent=2)
        print("Zapisano do: research_output.json")
        
    elif command == "verify" and len(sys.argv) >= 3:
        research_json = sys.argv[2]
        research = json.loads(research_json)
        
        print(f"\nWeryfikuję badanie: {research.get('title', 'N/A')}\n")
        result = manager.verify_research(research)
        
        print(f"Istnieje: {result.get('exists', False)}")
        print(f"Pewność: {result.get('confidence', 0)}%")
        print(f"Uzasadnienie: {result.get('reasoning', 'N/A')}")
        if result.get('alternative_source'):
            print(f"Alternatywne źródło: {result.get('alternative_source')}")
    
    else:
        print("Invalid command. Use 'search' or 'verify'")


if __name__ == "__main__":
    main()
