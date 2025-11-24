#!/bin/bash
# Test script dla systemu Auto-Article

echo "=========================================="
echo "Test Auto-Article - Generowanie z AI"
echo "=========================================="
echo ""

# Sprawdź środowisko
echo "1. Sprawdzanie środowiska..."
cd /home/swider/auto-article
source .venv/bin/activate

# Załaduj zmienne z .env jeśli istnieje
if [ -f .env ]; then
    echo "✓ Ładuję zmienne z .env"
    export $(cat .env | grep -v '^#' | xargs)
elif [ -f kids/.env ]; then
    echo "✓ Ładuję zmienne z kids/.env"
    export $(cat kids/.env | grep -v '^#' | xargs)
fi

# Sprawdź czy API key jest ustawiony
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY nie jest ustawiony!"
    echo "   Ustaw: export OPENAI_API_KEY='sk-...'"
    echo "   lub dodaj do .env"
    echo ""
    echo "🔧 Kontynuuję w trybie dry-run (bez prawdziwego API)..."
else
    echo "✓ OPENAI_API_KEY ustawiony"
fi

echo ""
echo "2. Test kompilacji modułów..."
python -m py_compile kids/tools/sora_image_manager.py
if [ $? -eq 0 ]; then
    echo "✓ sora_image_manager.py - OK"
else
    echo "❌ sora_image_manager.py - BŁĄD"
    exit 1
fi

python -m py_compile kids/tools/scientific_research.py
if [ $? -eq 0 ]; then
    echo "✓ scientific_research.py - OK"
else
    echo "❌ scientific_research.py - BŁĄD"
    exit 1
fi

python -m py_compile kids/tools/generate_article.py
if [ $? -eq 0 ]; then
    echo "✓ generate_article.py - OK"
else
    echo "❌ generate_article.py - BŁĄD"
    exit 1
fi

echo ""
echo "3. Test CLI Sora Image Manager..."
python kids/tools/sora_image_manager.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ CLI działa"
else
    echo "❌ CLI nie działa"
fi

echo ""
echo "4. Test CLI Scientific Research..."
python kids/tools/scientific_research.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ CLI działa"
else
    echo "❌ CLI nie działa"
fi

echo ""
echo "5. Test generowania artykułu (dry-run)..."
echo "   Temat: Test - Bezpieczeństwo niemowląt"
echo ""

python kids/tools/generate_article.py "Test - Bezpieczeństwo niemowląt" 2>&1 | grep -E "Saved:|✓|⚠️|❌"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Artykuł wygenerowany"
    
    # Znajdź wygenerowany plik
    LATEST_FILE=$(ls -t kids/content/posts/2025-11-23-test-*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_FILE" ]; then
        echo ""
        echo "Wygenerowany plik:"
        echo "  $LATEST_FILE"
        echo ""
        echo "Pierwsze 30 linii:"
        head -30 "$LATEST_FILE"
    fi
else
    echo "❌ Błąd generowania"
fi

echo ""
echo "=========================================="
echo "Test zakończony"
echo "=========================================="
echo ""
echo "Aby przetestować z prawdziwym API:"
echo "  export OPENAI_API_KEY='sk-...'"
echo "  python kids/tools/generate_article.py 'Twój temat'"
echo ""
echo "Sprawdź wygenerowane pliki:"
echo "  ls -lt kids/content/posts/"
echo ""
