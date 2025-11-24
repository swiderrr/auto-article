# Zmiany w Aplikacji Auto-Article

# Changelog

## 2025-11-24 - Poprawa jakości źródeł + Unsplash API + Europe PMC

### Naprawione błędy
- ✅ **Unsplash API**: Dodano wsparcie dla oficjalnego API Unsplash (wymaga UNSPLASH_ACCESS_KEY)
- ✅ **Filtrowanie źródeł**: Automatyczne odrzucanie nieistotnych publikacji (literatura, poezja, biografie)
- ✅ **Weryfikacja medyczna**: Sprawdzanie czy źródła dotyczą pediatrii/rodzicielstwa przed akceptacją
- ✅ **Europe PMC**: Dodano bazę Europe PMC (biomedycyna i nauki biologiczne)
- ✅ **Priorytet medyczny**: PubMed i Europe PMC przeszukiwane w pierwszej kolejności

### Nowe bazy danych medycznych
- 🏥 **Europe PMC** (European PubMed Central) - biomedycyna, nauki biologiczne, otwarte publikacje

### Zmiany techniczne
- Dodano `search_europepmc()` dla badań biomedycznych
- Rozszerzona weryfikacja słów kluczowych (relevant_keywords, irrelevant_keywords)
- Unsplash: wsparcie dla oficjalnego API + fallback do source.unsplash.com
- Dodano wielokrotne warianty słów kluczowych dla obrazów Unsplash
- Filtrowanie nieistotnych źródeł przed dodaniem do listy wyników

## 2025-11-24 - Integracja z bazami danych naukowych + Wymagania jakości

### Nowe funkcje - Bazy danych
- ✅ **Integracja z PubMed**: Bezpośrednie wyszukiwanie artykułów medycznych (baza NCBI)
- ✅ **Integracja z CrossRef**: Dostęp do międzynarodowych publikacji z DOI
- ✅ **Integracja z Semantic Scholar**: AI-powered baza multidyscyplinarna
- ✅ **Automatyczne deduplikacja**: System usuwa duplikaty na podstawie DOI/tytułu
- ✅ **AI-generowane streszczenia**: Automatyczne tłumaczenie głównych wniosków na polski
- ✅ **Wyszukiwanie dwujęzyczne**: Najpierw PL, potem EN

### Nowe funkcje - Wymagania jakości
- ✅ **Weryfikacja źródeł**: Artykuły generowane TYLKO gdy znajdą się badania naukowe (>50% confidence)
- ✅ **Brak źródeł = brak artykułu**: System odmawia generacji bez wiarygodnych badań
- ✅ **Sugestie tematów**: Gdy temat nie ma źródeł, system proponuje alternatywy
- ✅ **Widoczna informacja o źródłach**: Banner z informacją o bazach PubMed/CrossRef/Semantic Scholar
- ✅ **SEO z informacją o badaniach**: Meta opisy zawierają informację o oparciu na badaniach
- ✅ **Footer z linkami**: Stopka strony zawiera linki do baz danych naukowych

### Zmiany techniczne
- Dodano metody: `search_pubmed()`, `search_crossref()`, `search_semantic_scholar()`
- Dodano `_translate_topic_to_english()` dla lepszych wyników wyszukiwania
- Rozszerzone metadane artykułów: `database`, `pmid`, `doi`, `url`, `research_databases`
- Rate limiting dla API (0.5s pomiędzy zapytaniami)
- Weryfikacja > 50% confidence score dla AI-generated results
- `generate_article()` zwraca `None` gdy brak badań naukowych
- Zaktualizowany layout `single.html` z widocznym bannerem źródeł
- Zaktualizowany `footer.html` z linkami do baz danych
- Zaktualizowany `seo.html` z informacją o bazach w meta description

## 2025-11-23 - Priorytet Unsplash nad Pexels

### Podsumowanie zmian

Wprowadzono trzy główne usprawnienia do systemu generowania artykułów dla bloga Poradnik Rodzica:

1. **Naprawiono wyświetlanie favicon** na stronie
2. **Integracja obrazów z Sora** (zamiast Pexels/Unsplash)
3. **Artykuły oparte na badaniach naukowych** z bibliografią i weryfikacją źródeł

---

## 1. Naprawa Favicon ✅

### Problem
Favicon nie wyświetlał się na stronie www.poradnik-rodzica.com.pl

### Rozwiązanie
- Utworzono katalog `/kids/static/icons/` z pełnym zestawem ikon
- Wygenerowano wszystkie wymagane rozmiary favicon:
  - `favicon-16x16.png`
  - `favicon-32x32.png`
  - `favicon.ico`
  - `apple-touch-icon.png` (180x180)
  - `android-chrome-192x192.png`
  - `android-chrome-512x512.png`
- Dodano `site.webmanifest` dla Progressive Web App

### Lokalizacja plików
```
kids/static/
├── icons/
│   ├── favicon-16x16.png
│   ├── favicon-32x32.png
│   ├── favicon.ico
│   ├── apple-touch-icon.png
│   ├── android-chrome-192x192.png
│   ├── android-chrome-512x512.png
│   └── source.png (plik źródłowy)
└── site.webmanifest
```

### Aby zmienić favicon
1. Umieść nowy obraz (512x512 px, PNG) jako `kids/static/icons/source.png`
2. Uruchom: `python tools/generate_favicons.py`

---

## 2. Integracja Obrazów Sora ✅

### Problem
System korzystał z Pexels i innych fallback źródeł obrazów, co wymagało kluczy API i czasami przynosiło nieadekwatne zdjęcia.

### Rozwiązanie
- Utworzono menedżer obrazów Sora: `kids/tools/sora_image_manager.py`
- System najpierw sprawdza lokalne obrazy Sora, potem używa fallback (Pexels/Unsplash)
- Dodano katalog `/kids/static/img/sora/` dla obrazów generowanych przez Sora

### Jak korzystać

#### Dodawanie obrazów Sora
```bash
cd /home/swider/auto-article
source .venv/bin/activate

# Dodaj obraz z opisem
python kids/tools/sora_image_manager.py add /ścieżka/do/obrazu.jpg "Opis obrazu"

# Wyświetl listę dostępnych obrazów
python kids/tools/sora_image_manager.py list
```

#### Ręczne dodawanie
Możesz też ręcznie dodać obrazy do `kids/static/img/sora/`:
1. Skopiuj obraz (JPG/PNG) do `kids/static/img/sora/`
2. Opcjonalnie: utwórz plik `.json` z tym samym nazwą z metadanymi:
```json
{
  "description": "Opis obrazu",
  "keywords": ["tag1", "tag2"],
  "source": "sora.chatgpt.com"
}
```

#### Podczas generowania artykułu
System automatycznie:
1. Sprawdza dostępne obrazy Sora
2. Wybiera losowo 4 obrazy
3. Kopiuje je do katalogu artykułu
4. Jeśli nie ma obrazów Sora, używa Pexels/Unsplash jako fallback

---

## 3. Artykuły Oparte na Badaniach Naukowych ✅

### Implementacja

Dodano kompleksowy system integracji badań naukowych w artykułach:

#### Nowy moduł: `scientific_research.py`
Lokalizacja: `kids/tools/scientific_research.py`

**Funkcje:**
- `search_research()` - Wyszukuje prawdziwe badania naukowe za pomocą AI
- `verify_research()` - Weryfikuje autentyczność badań (ocena 0-100%)
- `generate_bibliography()` - Generuje sekcję bibliografii w formacie markdown
- `integrate_research_into_article()` - Dodaje cytowania [1], [2] w tekście

#### Zmodyfikowany `generate_article.py`

**Nowe funkcje:**
- Parametr `use_research=True` w funkcji `generate_article()`
- Automatyczne wyszukiwanie 3 badań naukowych dla tematu
- Weryfikacja każdego badania (tylko >50% pewności są używane)
- Dodawanie bibliografii na końcu artykułu
- Cytowania w tekście artykułu [1], [2], [3]

### Jak korzystać

#### Generowanie artykułu z badaniami (domyślnie włączone)
```bash
cd /home/swider/auto-article
source .venv/bin/activate

# Standardowe generowanie (z badaniami)
python kids/tools/generate_article.py "Temat artykułu"
```

#### Wyłączenie badań naukowych
```bash
# Ustaw zmienną środowiskową
export USE_RESEARCH=false
python kids/tools/generate_article.py "Temat artykułu"
```

#### Testowanie wyszukiwania badań
```bash
# Wyszukaj badania dla tematu
python kids/tools/scientific_research.py search "rozwój niemowląt"

# Wynik zostanie zapisany do research_output.json
```

### Proces weryfikacji

1. **Wyszukiwanie:** AI (GPT-4) wyszukuje prawdziwe, istniejące badania
2. **Weryfikacja:** Każde badanie jest weryfikowane pod kątem autentyczności
3. **Filtrowanie:** Tylko badania z pewnością >50% są używane
4. **Integracja:** Badania są cytowane w tekście artykułu
5. **Bibliografia:** Kompletna lista źródeł na końcu artykułu

### Format bibliografii

Artykuły zawierają teraz sekcję:

```markdown
## Bibliografia

*Artykuł oparty na następujących źródłach naukowych:*

1. Nazwisko A., Nazwisko B. (2023). *Tytuł badania*. Nazwa Czasopisma. DOI: [10.xxxx/xxxxx](https://doi.org/10.xxxx/xxxxx)

2. Nazwisko C. (2022). *Inny tytuł*. [Link do publikacji](https://...)
```

---

## Zmienne Środowiskowe

### Konfiguracja w `.env` lub environment:

```bash
# Wymagane dla generowania artykułów
OPENAI_API_KEY=sk-...

# Opcjonalne - dla obrazów fallback
PEXELS_API_KEY=...

# Opcjonalne - dla S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-north-1
S3_BUCKET=auto-article-kids

# Kontrola funkcji badań naukowych
USE_RESEARCH=true  # true/false, domyślnie true
```

---

## Struktura Plików

```
/home/swider/auto-article/
├── kids/
│   ├── static/
│   │   ├── icons/              # Favicon (NOWE)
│   │   │   ├── favicon-*.png
│   │   │   ├── apple-touch-icon.png
│   │   │   └── source.png
│   │   ├── img/
│   │   │   └── sora/           # Obrazy Sora (NOWE)
│   │   └── site.webmanifest    # PWA manifest (NOWE)
│   │
│   ├── tools/
│   │   ├── generate_article.py         # ZMODYFIKOWANY
│   │   ├── sora_image_manager.py       # NOWY
│   │   └── scientific_research.py      # NOWY
│   │
│   └── hugo.toml
│
├── tools/
│   └── generate_favicons.py
│
├── create_source_favicon.py    # NOWY - generator favicon
└── requirements.txt
```

---

## Testowanie

### Test 1: Favicon
1. Zbuduj stronę: `cd kids && hugo`
2. Sprawdź czy w `public/icons/` są wszystkie pliki
3. Deploy na serwer i sprawdź w przeglądarce

### Test 2: Obrazy Sora
```bash
# Dodaj testowy obraz
python kids/tools/sora_image_manager.py add /ścieżka/obraz.jpg "Test"

# Generuj artykuł
python kids/tools/generate_article.py "Test artykuł"

# Sprawdź czy używa obrazów Sora
```

### Test 3: Badania naukowe
```bash
# Generuj artykuł z badaniami
python kids/tools/generate_article.py "Sen niemowląt"

# Sprawdź wygenerowany plik markdown - powinien zawierać:
# - Cytowania [1], [2] w tekście
# - Sekcję ## Bibliografia na końcu
```

---

## Wymagania

### Zainstalowane pakiety (requirements.txt)
```
openai>=1.0.0
pillow>=12.0.0
boto3
requests
toml
pyyaml
```

### Instalacja
```bash
cd /home/swider/auto-article
source .venv/bin/activate
pip install -r requirements.txt
```

---

## FAQ

### Q: Czy muszę mieć obrazy Sora?
A: Nie - jeśli nie ma obrazów Sora, system automatycznie użyje Pexels/Unsplash jako fallback.

### Q: Czy badania naukowe są prawdziwe?
A: System używa GPT-4 do wyszukania prawdziwych badań i weryfikuje je z oceną pewności. Jednak zalecamy ręczną weryfikację kluczowych cytowań.

### Q: Jak wyłączyć badania naukowe?
A: Ustaw `export USE_RESEARCH=false` przed uruchomieniem skryptu.

### Q: Gdzie znajdę wygenerowane artykuły?
A: W `kids/content/posts/YYYY-MM-DD-slug-artykulu.md`

### Q: Jak zmienić liczbę badań w artykule?
A: W `generate_article.py`, zmień `count=3` w linii:
```python
research_list = research_mgr.search_research(topic, count=3)
```

---

## Troubleshooting

### Problem: Favicon nie wyświetla się
**Rozwiązanie:**
1. Sprawdź czy pliki istnieją w `kids/static/icons/`
2. Przebuduj stronę: `cd kids && hugo`
3. Wyczyść cache przeglądarki (Ctrl+Shift+R)

### Problem: Brak obrazów Sora
**Rozwiązanie:**
1. Dodaj obrazy do `kids/static/img/sora/`
2. Lub pozwól systemowi użyć Pexels (ustaw `PEXELS_API_KEY`)

### Problem: Błąd weryfikacji badań
**Rozwiązanie:**
1. Sprawdź czy `OPENAI_API_KEY` jest ustawiony
2. Sprawdź limity API OpenAI
3. Możesz wyłączyć weryfikację w kodzie (zakomentuj sekcję verify)

### Problem: Artykuł bez bibliografii
**Możliwe przyczyny:**
1. `USE_RESEARCH=false` - sprawdź zmienne środowiskowe
2. Brak klucza OpenAI API
3. Weryfikacja odrzuciła wszystkie badania (< 50% pewności)

---

## Kontakt i Wsparcie

W przypadku pytań lub problemów:
1. Sprawdź logi w terminalu podczas generowania
2. Zobacz przykładowe artykuły w `kids/content/posts/`
3. Przetestuj każdy moduł osobno (Sora, Research, Generate)

---

**Ostatnia aktualizacja:** 23 listopada 2025
**Wersja:** 2.0
**Status:** Wszystkie zmiany wdrożone i przetestowane ✅
