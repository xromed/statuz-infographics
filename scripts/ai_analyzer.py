"""
Анализирует текст статьи без AI — regex + ключевые слова.
Полностью бесплатно.
"""
import re


CATEGORIES = {
    "Цены":            ["цен", "инфляц", "ипц", "индекс цен", "плов"],
    "Демография":      ["населен", "рождаем", "смертност", "возраст", "брак", "семь"],
    "Промышленность":  ["промышленн", "производств", "завод", "предприяти", "пищев"],
    "Торговля":        ["торговл", "экспорт", "импорт", "товарооборот", "услуг"],
    "Здравоохранение": ["здравоохран", "медицин", "больниц", "врач", "лечен"],
    "Образование":     ["образован", "школ", "студент", "учебн", "вуз"],
    "Экономика":       ["ввп", "экономик", "валовой", "бюджет", "инвестиц"],
    "Спорт":           ["спорт", "атлет", "олимп", "чемпион"],
    "Туризм":          ["туризм", "турист", "посетил", "путешеств"],
    "Занятость":       ["занятост", "безработ", "труд", "работ", "зарплат"],
}

UNITS = ["трлн", "млрд", "млн", "тыс", "%", "процент", "чел", "предприяти", "компани"]

MONTHS_RU = {
    "января": "январь", "февраля": "февраль", "марта": "март",
    "апреля": "апрель", "мая": "май", "июня": "июнь",
    "июля": "июль", "августа": "август", "сентября": "сентябрь",
    "октября": "октябрь", "ноября": "ноябрь", "декабря": "декабрь",
}


def _detect_category(text: str) -> str:
    t = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in t for kw in keywords):
            return cat
    return "Статистика"


def _extract_numbers(text: str) -> list[dict]:
    """Ищет числа с единицами измерения в тексте."""
    results = []
    # Паттерн: число + единица (трлн сумов, млн человек, % и т.д.)
    pattern = r'([\d][.\d\s,]*\d?)\s*(трлн|млрд|млн|тыс\.?|процент[а-я]*|%)[.\s]*([а-яёА-ЯЁ\s]{0,30})?'
    for m in re.finditer(pattern, text, re.IGNORECASE):
        val = m.group(1).strip().replace(" ", "")
        unit = m.group(2).strip()
        context = m.group(3).strip() if m.group(3) else ""

        # Ищем метку — предложение перед числом
        start = max(0, m.start() - 120)
        snippet = text[start:m.start()].strip()
        # Берём последнее предложение/фразу
        parts = re.split(r'[.!?\n]', snippet)
        label = parts[-1].strip() if parts else snippet
        label = label[-60:].lstrip(" ,;:—")

        if val and unit:
            results.append({
                "value": val,
                "unit": unit + (" " + context[:20] if context else ""),
                "label": label or "Показатель",
                "trend": "neutral",
            })

    return results[:6]


def _detect_period(text: str) -> str:
    """Извлекает упоминание периода."""
    # "за N месяц(а/ев) YYYY" или "май 2026" и т.д.
    m = re.search(r'за\s+(\d+)\s+месяц[а-я]*\s+(\d{4})', text, re.IGNORECASE)
    if m:
        return f"январь–{'апрель февраль март апрель май июнь'.split()[int(m.group(1))-1]} {m.group(2)}"

    m = re.search(
        r'(январ[а-я]+|феврал[а-я]+|март[а-я]*|апрел[а-я]+|ма[йя]|июн[а-я]+|'
        r'июл[а-я]+|август[а-я]*|сентябр[а-я]+|октябр[а-я]+|ноябр[а-я]+|декабр[а-я]+)'
        r'\s+(\d{4})',
        text, re.IGNORECASE
    )
    if m:
        return f"{m.group(1)} {m.group(2)}"

    m = re.search(r'(\d{4})\s*год[а-я]*', text)
    if m:
        return f"{m.group(1)} год"

    return ""


def _make_headline(title: str) -> str:
    """Укорачивает заголовок до разумной длины."""
    t = title.strip()
    if len(t) <= 70:
        return t
    # Обрезаем по словам
    words = t.split()
    result = []
    for w in words:
        result.append(w)
        if len(" ".join(result)) > 65:
            result.pop()
            break
    return " ".join(result) + "…"


def analyze(title: str, body: str, tables: list) -> dict:
    """Возвращает структурированные данные для инфографики."""
    full_text = title + "\n" + body

    category = _detect_category(full_text)
    period = _detect_period(full_text)
    key_stats = _extract_numbers(full_text)

    # Добавляем числа из таблиц
    if tables and len(key_stats) < 4:
        for row in tables[0][:5]:
            nums = [c for c in row if re.search(r'\d', str(c))]
            labels = [c for c in row if c and not re.search(r'^\d', str(c))]
            if nums and labels:
                key_stats.append({
                    "value": str(nums[0]),
                    "unit": "",
                    "label": str(labels[0])[:50],
                    "trend": "neutral",
                })

    # Главная цифра — первое и самое большое число
    main_value, main_unit = "", ""
    if key_stats:
        main_value = key_stats[0]["value"]
        main_unit = key_stats[0]["unit"]

    return {
        "headline": _make_headline(title),
        "category": category,
        "main_value": main_value,
        "main_unit": main_unit,
        "period": period,
        "key_stats": key_stats,
        "chart_type": "bar" if len(key_stats) >= 3 else "none",
    }
