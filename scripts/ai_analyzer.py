"""
Анализирует текст статьи без AI — regex + ключевые слова.
Полностью бесплатно.
"""
import re


CATEGORIES = {
    "Цены":            [r"\bцен[аыу]?\b", r"\bинфляц", r"\bипц\b", r"\bиндекс цен"],
    "Демография":      [r"\bнаселен", r"\bрождаем", r"\bсмертност", r"\bбрак[аеу]?\b", r"\bмиграц"],
    "Промышленность":  [r"\bпромышленн", r"\bпроизводств", r"\bзавод", r"\bпредприяти", r"\bпищев", r"\bгорнодобыв"],
    "Транспорт":       [r"\bтранспорт", r"\bжелезнодорожн", r"\bавиа", r"\bгруз[аыуов]", r"\bперевоз"],
    "Торговля":        [r"\bторговл", r"\bэкспорт", r"\bимпорт", r"\bтоварооборот"],
    "Здравоохранение": [r"\bздравоохран", r"\bмедицин", r"\bбольниц", r"\bврач", r"\bлечен"],
    "Образование":     [r"\bобразован", r"\bшкол", r"\bстудент", r"\bучебн", r"\bвуз"],
    "Экономика":       [r"\bввп\b", r"\bэкономик", r"\bвалово[йег]", r"\bбюджет", r"\bинвестиц"],
    "Спорт":           [r"\bспорт", r"\bатлет", r"\bолимп", r"\bчемпион"],
    "Туризм":          [r"\bтуризм", r"\bтурист", r"\bпосетил", r"\bпутешеств"],
    "Занятость":       [r"\bзанятост", r"\bбезработ", r"\bзарплат", r"\bдоход"],
    "Сельское хозяйство": [r"\bсельск", r"\bагро", r"\bурожай", r"\bземледел", r"\bскотовод"],
    "Строительство":   [r"\bстроительств", r"\bжильё\b", r"\bжилищн", r"\bсдано.*м²"],
}

UNITS = ["трлн", "млрд", "млн", "тыс", "%", "процент", "чел", "предприяти", "лет", "года", "год"]

MONTHS_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
MONTH_NAMES = ["", "январь", "февраль", "март", "апрель", "май", "июнь",
               "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


def _detect_category(text: str) -> str:
    t = text.lower()
    scores = {}
    for cat, patterns in CATEGORIES.items():
        score = sum(1 for p in patterns if re.search(p, t))
        if score:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "Статистика"


def _extract_numbers(text: str) -> list:
    """Ищет числа с единицами измерения в тексте."""
    results = []
    # Паттерн 1: обычный — число потом единица
    # НЕ включаем "лет|года" здесь — обрабатываем отдельно ниже
    # (?!\w) после "тыс" не даёт словам вроде "тысячу"/"тысяча" ложно матчиться как "тыс" + обрывок
    pattern = r'([\d][\d\s.,]*\d?)\s*(трлн|млрд|млн|тыс\.?(?!\w)|процент[а-я]*|%)\s*([а-яёА-ЯЁ]{1,12})?'
    # Паттерн для продолжительности жизни и возрастных показателей
    duration_pattern = r'([\d]{1,3}[.,]\d)\s*(лет|года?)\b'
    # Паттерн 2: "Название - ЧИСЛО единица" (региональные данные)
    regional_pattern = r'([А-ЯЁа-яёA-Za-z][^\n\-–—]{2,40})\s*[-–—]\s*([\d][,.\d]*)\s*(трлн|млрд|млн|тыс\.?(?!\w))\s*([а-яёА-ЯЁ]{0,12})'
    seen_vals = set()

    for m in re.finditer(pattern, text, re.IGNORECASE):
        val = m.group(1).strip().replace(" ", "").replace(",", ".")
        try:
            fval = float(val)
        except ValueError:
            continue

        # Игнорируем годы (1900–2099)
        if 1900 <= fval <= 2099:
            continue

        unit = m.group(2).strip()
        # Контекст — только первое слово после единицы (напр. "сумов", "долларов")
        context_word = (m.group(3) or "").strip()
        # Убираем слова не похожие на существительные (короткие предлоги и т.д.)
        if context_word and len(context_word) < 3:
            context_word = ""

        # Убираем дубликаты по значению
        key = f"{val}{unit}"
        if key in seen_vals:
            continue
        seen_vals.add(key)

        # Ищем метку — фраза перед числом (последнее предложение)
        start = max(0, m.start() - 120)
        snippet = text[start:m.start()].strip()
        parts = re.split(r'[.!?\n]', snippet)
        label = parts[-1].strip().lstrip(" ,;:—")[-60:]

        # Определяем тренд
        trend = "neutral"
        ctx_before = text[max(0, m.start()-80):m.start()].lower()
        if re.search(r'вырос|увелич|прирост|рост|повыс|больше', ctx_before):
            trend = "up"
        elif re.search(r'снизил|уменьш|сократил|упал|меньше|снижен', ctx_before):
            trend = "down"

        full_unit = (unit + " " + context_word).strip()
        if val and unit:
            results.append({
                "value": val,
                "unit": full_unit,
                "label": label or "Показатель",
                "trend": trend,
            })

    # Паттерн для "лет/года" — только дробные числа, не годы
    for m in re.finditer(duration_pattern, text, re.IGNORECASE):
        val = m.group(1).replace(",", ".")
        try:
            fval = float(val)
        except ValueError:
            continue
        if 1900 <= fval <= 2099:
            continue
        unit = m.group(2).strip()
        key = f"{val}{unit}"
        if key in seen_vals:
            continue
        seen_vals.add(key)
        start = max(0, m.start() - 120)
        snippet = text[start:m.start()].strip()
        parts = re.split(r'[.!?\n]', snippet)
        label = parts[-1].strip().lstrip(" ,;:—")[-60:]
        trend = "neutral"
        ctx_before = text[max(0, m.start()-80):m.start()].lower()
        if re.search(r'вырос|увелич|прирост|рост|повыс|больше', ctx_before):
            trend = "up"
        results.append({"value": val, "unit": unit, "label": label or "Показатель", "trend": trend})

    # Паттерн 2: региональные данные "Название - 12,7 трлн сумов"
    for m in re.finditer(regional_pattern, text, re.IGNORECASE | re.MULTILINE):
        label = m.group(1).strip().rstrip(" \t-–—")[-55:]
        val   = m.group(2).replace(",", ".")
        ctx4  = (m.group(4) or "").strip()
        unit  = m.group(3) + (" " + ctx4 if ctx4 and len(ctx4) >= 3 else "")
        key   = f"{val}{m.group(3)}"
        if key in seen_vals:
            continue
        try:
            float(val)
        except ValueError:
            continue
        seen_vals.add(key)
        results.append({
            "value": val,
            "unit":  unit.strip(),
            "label": label,
            "trend": "neutral",
        })

    return results[:12]


def _extract_grouped_counts(text: str) -> list:
    """Резервный поиск: числа с разделителем групп разрядов (18 330, 191 521, 5 351 868)
    и следующим словом (или двумя) как единицей — «человек», «граждан», «ремесленников»,
    «иностранных граждан» и т.п. Пробел-разделитель разрядов надёжно отличает такие числа
    от годов (1900-2099 никогда не пишутся с пробелом)."""
    results = []
    seen = set()
    pattern = r'([\d]{1,3}(?:[ \t]\d{3})+)[ \t]+([а-яёА-ЯЁ]{2,20}(?:[ \t][а-яёА-ЯЁ]{2,20})?)'
    for m in re.finditer(pattern, text):
        val = re.sub(r'[ \t ]', '', m.group(1))
        try:
            float(val)
        except ValueError:
            continue
        unit = m.group(2).strip()
        key = f"{val}{unit}"
        if key in seen:
            continue
        seen.add(key)
        start = max(0, m.start() - 120)
        snippet = text[start:m.start()].strip()
        parts = re.split(r'[.!?\n]', snippet)
        label = parts[-1].strip().lstrip(" ,;:—-")[-60:]
        trend = "neutral"
        ctx_before = text[max(0, m.start() - 80):m.start()].lower()
        if re.search(r'вырос|увелич|прирост|рост|повыс|больше', ctx_before):
            trend = "up"
        elif re.search(r'снизил|уменьш|сократил|упал|меньше|снижен', ctx_before):
            trend = "down"
        results.append({"value": val, "unit": unit, "label": label or "Показатель", "trend": trend})
    return results


def _extract_dash_items(text: str) -> list:
    """Резервный поиск построчных перечислений вида «Ташкент - 12 480 предприятий».
    Разбивает по строкам/точкам с запятой и берёт ПОСЛЕДНИЙ дефис в строке как разделитель —
    это корректно обрабатывает метки с внутренним дефисом вроде «0-18 лет - 584 171 человек»."""
    results = []
    seen = set()
    for raw_line in re.split(r'[\n;]+', text):
        line = raw_line.strip().rstrip('.').strip()
        if not line or len(line) > 120:
            continue
        m = re.search(
            r'^(.*)[-–—]\s*([\d][\d\s.,]*\d|\d+)\s*([а-яёА-ЯЁ.]{2,20})?\s*$',
            line
        )
        if not m:
            continue
        label = m.group(1).strip(" ,:;")
        if not label or len(label) > 60 or len(label) < 2:
            continue
        val = m.group(2).strip().replace(" ", "").replace(",", ".")
        try:
            fval = float(val)
        except ValueError:
            continue
        unit = (m.group(3) or "").strip()
        if 1900 <= fval <= 2099 and not unit:
            continue  # похоже на голый год
        key = f"{val}{unit}{label}"
        if key in seen:
            continue
        seen.add(key)
        results.append({"value": val, "unit": unit, "label": label[:55], "trend": "neutral"})
    return results


def _detect_period(text: str) -> str:
    # "за N месяц(а/ев) YYYY"
    m = re.search(r'за\s+(\d+)\s+месяц[а-я]*\s+(\d{4})', text, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        y = m.group(2)
        if 1 <= n <= 12:
            return f"январь–{MONTH_NAMES[n]} {y}"

    m = re.search(
        r'(январ[а-я]+|феврал[а-я]+|март[а-я]*|апрел[а-я]+|ма[йя]|июн[а-я]+|'
        r'июл[а-я]+|август[а-я]*|сентябр[а-я]+|октябр[а-я]+|ноябр[а-я]+|декабр[а-я]+)'
        r'\s+(\d{4})',
        text, re.IGNORECASE
    )
    if m:
        return f"{m.group(1).lower()} {m.group(2)}"

    m = re.search(r'(\d{4})\s*год[а-я]*', text)
    if m:
        return f"{m.group(1)} год"

    return ""


def _make_headline(title: str) -> str:
    t = title.strip()
    if len(t) <= 72:
        return t
    words = t.split()
    result = []
    for w in words:
        result.append(w)
        if len(" ".join(result)) > 68:
            result.pop()
            break
    return " ".join(result) + "…"


def _year_from_label(s: dict) -> int:
    """Извлекает год из метки показателя (для сортировки временных рядов)."""
    m = re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))
    return int(m.group()) if m else 9999


def _build_chart_data(key_stats: list) -> list:
    """Выбирает показатели для диаграммы.

    Два режима:
    1) Временной ряд — только показатели с реально распознанным годом
       в подписи. Остальные (заголовок-итог, нечисловые ярлыки) сюда
       никогда не попадают, иначе на line-графике year-точки вперемешку
       с произвольным текстом рисуются как единая гладкая кривая.
       Пропущенные годы внутри диапазона заполняются None (разрыв на
       графике), чтобы не "заглаживать" дыры в данных.
    2) Структура/части — сравнение категорий (регионы, отрасли и т.п.).
       Первый показатель (key_stats[0]) почти всегда совпадает с главной
       цифрой в заголовке ("Х достигло N трлн сумов") — это ИТОГ, а не
       сравнимая категория, поэтому в диаграмму частей он не включается
       (иначе "итого" рисуется как ещё один бар рядом со своими же
       составляющими).
    """
    if not key_stats:
        return []

    dated = [s for s in key_stats if _year_from_label(s) != 9999]
    if len(dated) >= 2:
        by_year = {}
        for s in dated:
            y = _year_from_label(s)
            if y not in by_year:  # первое вхождение года
                by_year[y] = s
        years = sorted(by_year)
        if len(years) >= 2:
            span = years[-1] - years[0] + 1
            if span <= 12:
                filled = []
                for y in range(years[0], years[-1] + 1):
                    if y in by_year:
                        filled.append(by_year[y])
                    else:
                        filled.append({
                            "value": None,
                            "unit": dated[0].get("unit", ""),
                            "label": str(y),
                            "trend": "neutral",
                        })
                return filled[:12]
            return [by_year[y] for y in years][:8]

    from collections import defaultdict
    candidates = key_stats[1:] if len(key_stats) > 1 else key_stats
    groups = defaultdict(list)
    for s in candidates:
        unit_base = s["unit"].split()[0] if s["unit"] else "ед."
        if _safe_float(s["value"]) is not None:
            groups[unit_base].append(s)

    best = max(groups.values(), key=len, default=[])
    result = best[:8] if len(best) >= 2 else []

    if not result:
        result = [s for s in candidates if _safe_float(s["value"]) is not None][:8]

    return result


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _dehyphenate(text: str) -> str:
    """Склеивает слова, перенесённые по слогам через дефис на конце строки —
    типичный артефакт pdfplumber на многоколоночных PDF-релизах Госкомстата
    ("пере-\nписи" -> "переписи"). Без этого regex-экстрактор хватает
    случайные обрывки слов вокруг чисел вместо настоящих подписей."""
    text = re.sub(r'-\s*\n\s*(?=[а-яёa-z])', '', text)
    return text


def analyze(title: str, body: str, tables: list) -> dict:
    body = _dehyphenate(body)
    full_text = title + "\n" + body

    category = _detect_category(full_text)
    period = _detect_period(full_text)
    key_stats = _extract_numbers(full_text)

    # Резервные экстракторы — на случай единиц, которых нет в основном списке
    # (человек, граждан, предприятий, ремесленников и т.п.).
    # Работают только по body (не по заголовку) — заголовок часто пересказывает
    # то же число другими словами и иначе "перебивает" реальную единицу измерения.
    if len(key_stats) < 4:
        seen_vals = {s["value"] for s in key_stats}
        for extra in _extract_grouped_counts(body) + _extract_dash_items(body):
            if extra["value"] not in seen_vals:
                key_stats.append(extra)
                seen_vals.add(extra["value"])

    # Добавляем числа из таблиц
    if tables and len(key_stats) < 4:
        for row in tables[0][:6]:
            row_s = [str(c) for c in row if c]
            nums = [c for c in row_s if re.search(r'^[\d.,\s]+$', c.strip())]
            labels = [c for c in row_s if c and not re.search(r'^[\d.,\s]+$', c.strip())]
            if nums and labels:
                val = nums[0].strip().replace(",", ".").replace(" ", "")
                try:
                    float(val)
                    key_stats.append({
                        "value": val,
                        "unit": "",
                        "label": str(labels[0])[:55],
                        "trend": "neutral",
                    })
                except ValueError:
                    pass

    # Главная цифра — первый числовой показатель
    main_value, main_unit = "", ""
    if key_stats:
        main_value = key_stats[0]["value"]
        main_unit = key_stats[0]["unit"]

    chart_data = _build_chart_data(key_stats)

    return {
        "headline": _make_headline(title),
        "category": category,
        "main_value": main_value,
        "main_unit": main_unit,
        "period": period,
        "key_stats": key_stats,
        "chart_data": chart_data,
        "chart_type": "bar" if len(chart_data) >= 2 else "none",
    }
