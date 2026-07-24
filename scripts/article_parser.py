"""Загружает и парсит страницу статьи."""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

BASE = "https://stat.uz"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StatBot/1.0)"}

# Полное совпадение с этим текстом (без учёта регистра) означает, что мы
# выцепили не заголовок статьи, а название комитета из шапки/подвала сайта.
# Такой "заголовок" никогда не должен попадать в данные.
BAD_TITLE = "национальный комитет республики узбекистан по статистике"

# Этот блок — фиксированный подвал сайта (адрес комитета), он есть на любой
# странице. Используем его как надёжный правый ограничитель при вырезании
# текста статьи из текста всей страницы (см. фолбэк ниже).
FOOTER_MARKER = "Национальный комитет Республики Узбекистан по статистике"

# Минимальная длина текста статьи, ниже которой мы не доверяем результату
# основного парсинга (например "Loading..." — заглушка JS-виджета) и
# переключаемся на фолбэк по всей странице.
MIN_BODY_LEN = 40


def _extract_pdf_urls(node) -> list:
    """Ищет ссылки на PDF внутри переданного узла (может быть content или
    soup целиком — используется в обоих случаях)."""
    pdf_urls = []
    for iframe in node.find_all("iframe"):
        src = iframe.get("src", "")
        if "viewer.html" in src and "file=" in src:
            pdf_url = unquote(src.split("file=")[-1])
            if pdf_url.endswith(".pdf"):
                pdf_urls.append(pdf_url)

    for a in node.find_all("a", href=True):
        if a["href"].endswith(".pdf"):
            full = BASE + a["href"] if a["href"].startswith("/") else a["href"]
            if full not in pdf_urls:
                pdf_urls.append(full)

    return pdf_urls


def parse(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[parser] Ошибка: {e}")
        return {}

    soup = BeautifulSoup(r.text, "lxml")

    # Блок с телом статьи ищем в первую очередь: заголовок надёжнее всего
    # искать внутри него, а не по всей странице (в шапке и подвале сайта
    # тоже есть свои <h2>, включая "Национальный комитет Республики
    # Узбекистан по статистике" в подвале — его легко случайно принять за
    # заголовок при поиске по всему документу).
    content = (
        soup.find("div", class_="item-page")
        or soup.find("article")
        or soup.find("div", id="content")
    )

    # Основной источник заголовка — тег <title> страницы: на практике он
    # всегда содержит чистый заголовок статьи без служебных суффиксов вида
    # " | stat.uz".
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.get_text(strip=True)
        # На случай появления суффикса " | stat.uz" или похожего —
        # отрезаем всё после первого " | ".
        t = t.split(" | ")[0].strip()
        if t and t.strip().lower() != BAD_TITLE:
            title = t

    # Фолбэк: ищем <h2> только внутри блока статьи (не по всей странице),
    # чтобы не зацепить статичные заголовки шапки/подвала.
    if not title and content:
        for h2 in content.find_all("h2"):
            t = h2.get_text(strip=True)
            if t and t.strip().lower() != BAD_TITLE:
                title = t
                break

    # Защита: даже если что-то пошло не так выше, никогда не отдаём
    # название комитета в качестве заголовка статьи.
    if title.strip().lower() == BAD_TITLE:
        title = ""

    # Дата: ищем внутри блока статьи (content), а не по всей странице —
    # иначе можно случайно зацепить дату из сайдбара с "похожими новостями"
    # (там перечислены другие статьи с их собственными датами) вместо даты
    # текущей статьи. get_text() склеивает текст всех дочерних тегов, что
    # также решает проблему, когда дата на новом шаблоне stat.uz разбита
    # на несколько соседних HTML-узлов и не совпадает как одна строка.
    # День может быть однозначным (например "9 июля 2026"), поэтому \d{1,2},
    # а не \d{2}.
    date = ""
    date_source = content if content else soup
    date_text = date_source.get_text("\n", strip=True)
    m = re.search(r"(\d{1,2}\s+[а-яёА-ЯЁ]+\s+\d{4})", date_text)
    if m:
        date = m.group(1)

    body_text, pdf_urls, tables = "", [], []

    if content:
        pdf_urls = _extract_pdf_urls(content)

        for table in content.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        for tag in content(["script", "style", "iframe"]):
            tag.decompose()
        body_text = content.get_text("\n", strip=True)[:4000]

    # Фолбэк: на текущем шаблоне stat.uz div.item-page/article/#content
    # часто вообще не находится (content is None), либо находится, но тело
    # внутри него — просто JS-заглушка вида "Loading..." (реальный текст
    # подгружается скриптом, которого requests не исполняет). В обоих
    # случаях используем текст всей страницы и вырезаем статью между двумя
    # надёжными ориентирами: заголовком статьи (title, уже определён выше)
    # и неизменным подвалом сайта (FOOTER_MARKER), который встречается
    # ровно один раз — перед адресом комитета в самом низу страницы.
    if title and (not content or len(body_text.strip()) < MIN_BODY_LEN):
        full_text = soup.get_text("\n", strip=True)
        footer_idx = full_text.find(FOOTER_MARKER)
        if footer_idx != -1:
            # rfind — берём последнее вхождение заголовка ПЕРЕД подвалом:
            # это заголовок непосредственно над телом статьи, а не более
            # ранние упоминания (например в <title> страницы или в меню).
            title_idx = full_text.rfind(title, 0, footer_idx)
            if title_idx != -1:
                slice_start = title_idx + len(title)
                fallback_text = full_text[slice_start:footer_idx]
                # Убираем дату (уже извлечена отдельно в `date`) и голые
                # ссылки на PDF — это не текст статьи.
                fallback_text = re.sub(
                    r"^\s*\d{1,2}\s+[а-яёА-ЯЁ]+\s+\d{4}\s*", "", fallback_text
                )
                fallback_text = re.sub(r"https?://\S+", "", fallback_text).strip()
                fallback_text = re.sub(r"\n{2,}", "\n\n", fallback_text)

                # Если после чистки почти ничего не осталось — это чисто
                # PDF-релиз (страница содержит только "Loading..." и ссылку
                # на PDF, без инлайн-текста). В этом случае намеренно
                # оставляем body_text пустым, а не набиваем туда "Loading...":
                # для таких статей ничего не изменится, пока не появится
                # отдельная логика скачивания/OCR PDF.
                if len(fallback_text) >= MIN_BODY_LEN:
                    body_text = fallback_text[:4000]
                elif not content:
                    body_text = ""

        # Если content вообще не найден, ссылки на PDF нужно поискать по
        # всей странице (иначе pdf_urls потеряется вместе с content).
        if not content:
            pdf_urls = _extract_pdf_urls(soup)

    return {
        "title": title,
        "date": date,
        "body_text": body_text,
        "pdf_urls": pdf_urls,
        "tables": tables,
    }
