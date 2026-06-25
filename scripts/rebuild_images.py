"""
Пересоздаёт все картинки из существующей БД.
Запускать: python scripts/rebuild_images.py
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path("data/articles.json")

if not DB_PATH.exists():
    print("data/articles.json не найден, запускать из корня репозитория")
    sys.exit(1)

articles = json.loads(DB_PATH.read_text())
img_dir = Path("docs/news/img")

# Удаляем старые картинки чтобы generator их пересоздал
deleted = 0
for png in img_dir.glob("*.png"):
    png.unlink()
    deleted += 1
print(f"Удалено старых картинок: {deleted}")

import image_generator, site_builder

for a in articles:
    an = a.get("analysis", {})
    if not an:
        continue
    img = image_generator.generate(a["id"], an)
    an["img_path"] = img or ""

# Пересобираем HTML страницы тоже
for a in articles:
    an = a.get("analysis", {})
    if an:
        site_builder.build_article_page(a, an)

site_builder.build_index(articles)
print(f"\n✅ Пересоздано {len(articles)} статей")
