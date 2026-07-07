"""
Оркестратор. Запускается GitHub Actions каждые 3 часа.
Весь стейт хранится в data/articles.json (коммитится в репо).
"""
import json, time, os
from pathlib import Path

import scraper, article_parser, ai_analyzer, image_generator, site_builder, telegram_pub

DB_PATH = Path("data/articles.json")
PAGES_URL = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")


def load_db() -> list:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text())
    return []


def save_db(articles: list):
    DB_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2))


def known_ids(articles: list) -> set:
    return {a["id"] for a in articles}


def _fetch_and_analyze(article: dict) -> dict | None:
    """Скачивает статью и анализирует заново."""
    try:
        parsed = article_parser.parse(article["url"])
        if not parsed:
            return None
        all_text = parsed.get("body_text", "")
        all_tables = parsed.get("tables", [])
        for pdf_url in parsed.get("pdf_urls", [])[:1]:
            try:
                import pdfplumber, requests as req, tempfile
                r = req.get(pdf_url, timeout=20)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(r.content); tmp = f.name
                with pdfplumber.open(tmp) as pdf:
                    for page in pdf.pages[:5]:
                        t = page.extract_text()
                        if t: all_text += "\n" + t
                        for tbl in page.extract_tables():
                            if tbl: all_tables.append(tbl)
                os.unlink(tmp)
            except Exception:
                pass
        analysis = ai_analyzer.analyze(
            parsed.get("title") or article.get("title", ""),
            all_text, all_tables,
        )
        # Сохраняем текст для будущих пересборок
        article["body_text"]  = all_text[:8000]
        article["tables_raw"] = all_tables[:3]
        return analysis
    except Exception as e:
        print(f"  re-analyze error: {e}")
        return None


def rebuild_all_pages(db: list, reanalyze: bool = False):
    """Пересобирает HTML. Если reanalyze=True — перескачивает и переанализирует статьи без chart_data."""
    print("Пересобираем страницы...")
    changed = False
    BROKEN_HEADLINE = "республики узбекистан по статистике"
    for a in db:
        an = a.get("analysis", {})
        needs_reanalysis = (
            reanalyze and
            a.get("url") and                    # есть URL для перескачивания
            (
                not an.get("chart_data") or      # нет данных для диаграммы
                # заголовок = статичная шапка сайта — старый баг article_parser,
                # уже исправлен, но старые записи нужно перескачать заново
                an.get("headline", "").strip().lower() == BROKEN_HEADLINE
            )
        )
        if needs_reanalysis:
            print(f"  Re-analyze: {a['id']}")
            new_an = _fetch_and_analyze(a)
            if new_an:
                img_path = image_generator.generate(a["id"], new_an)
                new_an["img_path"] = img_path or ""
                a["analysis"] = new_an
                an = new_an
                changed = True
            time.sleep(1)

        if an:
            try:
                site_builder.build_article_page(a, an)
            except Exception as e:
                print(f"  [rebuild] {a['id']}: {e}")

    if db:
        site_builder.build_index(db)
    print(f"  ✓ {len(db)} страниц")
    return changed


def run():
    print("=== StatUZ Updater ===")
    db = load_db()
    ids = known_ids(db)

    # Пересобираем страницы; пере-анализируем те у кого нет chart_data
    reanalysis_changed = rebuild_all_pages(db, reanalyze=True)
    if reanalysis_changed:
        save_db(db)

    # Находим новые статьи
    fresh = scraper.fetch_news_list(pages=2)
    new_articles = [a for a in fresh if a["id"] not in ids]
    print(f"Новых статей: {len(new_articles)}")

    updated = False

    for article in new_articles[:10]:  # max 10 за раз (экономим DALL-E)
        print(f"\n→ {article['title'][:60]}")
        try:
            # 1. Парсим страницу
            parsed = article_parser.parse(article["url"])
            if not parsed:
                continue

            # 2. Анализируем через GPT
            all_text = parsed.get("body_text", "")
            all_tables = parsed.get("tables", [])

            # PDF — пробуем если есть
            for pdf_url in parsed.get("pdf_urls", [])[:1]:
                try:
                    import pdfplumber, requests, tempfile
                    r = requests.get(pdf_url, timeout=20)
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(r.content)
                        tmp = f.name
                    with pdfplumber.open(tmp) as pdf:
                        for page in pdf.pages[:5]:
                            t = page.extract_text()
                            if t:
                                all_text += "\n" + t
                            for tbl in page.extract_tables():
                                if tbl:
                                    all_tables.append(tbl)
                    os.unlink(tmp)
                except Exception as e:
                    print(f"  PDF ошибка: {e}")

            analysis = ai_analyzer.analyze(
                parsed.get("title") or article["title"],
                all_text,
                all_tables,
            )

            # Сохраняем текст для будущих пересборок/переанализа
            # (раньше это делалось только в _fetch_and_analyze при reanalyze=True,
            # из-за чего у свежедобавленных статей body_text оставался пустым)
            article["body_text"]  = all_text[:8000]
            article["tables_raw"] = all_tables[:3]

            # 3. Генерируем инфографику через matplotlib
            img_path = image_generator.generate(article["id"], analysis)
            analysis["img_path"] = img_path or ""

            # 4. Строим HTML страницу
            article["analysis"] = analysis
            site_builder.build_article_page(article, analysis)

            # 5. Добавляем в БД
            db.append(article)
            ids.add(article["id"])
            updated = True

            # 6. Публикуем в Telegram
            page_url = f"{PAGES_URL}/news/{article['id']}.html" if PAGES_URL else ""
            img_local = f"docs/news/{img_path}" if img_path else ""
            telegram_pub.post(article, analysis, page_url, img_local)

            time.sleep(3)  # небольшая пауза

        except Exception as e:
            print(f"  Ошибка: {e}")
            import traceback; traceback.print_exc()

    if updated:
        save_db(db)
        site_builder.build_index(db)
        print("\n✅ Обновление завершено")
    else:
        print("\nНовых статей нет")


if __name__ == "__main__":
    run()
