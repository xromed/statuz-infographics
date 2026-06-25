"""
Пересобирает все HTML страницы из articles.json.
Вызывается в GitHub Actions после обновления site_builder.py.
Картинки не трогает — только HTML.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path("data/articles.json")
if not DB_PATH.exists():
    print("data/articles.json не найден")
    sys.exit(0)

articles = json.loads(DB_PATH.read_text())
print(f"Пересобираем {len(articles)} страниц...")

import site_builder

for a in articles:
    an = a.get("analysis", {})
    if an:
        site_builder.build_article_page(a, an)

site_builder.build_index(articles)
print("✅ Готово")
