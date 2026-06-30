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
    pattern = r'([\d][\d\s.,]*\d?)\s*(трлн|млрд|млн|тыс\.?|процент[а-я]*|%)\s*([а-яёА-ЯЁ]{1,12})?'
    # Паттерн для продолжительности жизни и возрастных показателей
    duration_pattern = r'([\d]{1,3}[.,]\d)\s*(лет|года?)\b'
    # Паттерн 2: "Название - ЧИСЛО единица" (региональные данные)
    regional_pattern = r'([А-ЯЁа-яёA-Za-z][^\n\-–—]{2,40})\s*[-–—]\s*([\d][,.\d]*)\s*(трлн|млрд|млн|тыс\.?)\s*([а-яёА-ЯЁ]{0,12})'
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
    """Выбирает показатели с одинаковыми единицами для диаграммы."""
    if not key_stats:
        return []

    from collections import defaultdict
    groups = defaultdict(list)
    for s in key_stats:
        unit_base = s["unit"].split()[0] if s["unit"] else "ед."
        try:
            float(s["value"])
            groups[unit_base].append(s)
        except ValueError:
            pass

    best = max(groups.values(), key=len, default=[])
    result = best[:8] if len(best) >= 2 else []

    if not result:
        result = [s for s in key_stats if _safe_float(s["value"]) is not None][:8]

    # Если метки содержат годы — сортируем хронологически
    years = [_year_from_label(s) for s in result]
    if sum(1 for y in years if y != 9999) >= 2:
        result = sorted(result, key=_year_from_label)

    return result


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def analyze(title: str, body: str, tables: list) -> dict:
    full_text = title + "\n" + body

    category = _detect_category(full_text)
    period = _detect_period(full_text)
    key_stats = _extract_numbers(full_text)

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
