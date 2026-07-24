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


def _trim_label(text: str, max_len: int = 60) -> str:
    """Обрезает метку до max_len символов, но не посреди слова.
    Наивная нарезка text[-max_len:] может отрезать слово точно
    посередине (например «...года объем...» -> «...а объем...»,
    потеряв «год» и оставив висячую «а»). Если после обрезки
    первый символ — не начало слова, отбрасываем этот обрывок."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    trimmed = text[-max_len:]
    sp = trimmed.find(" ")
    if 0 < sp < 20:
        trimmed = trimmed[sp + 1:]
    return trimmed.strip()


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

    # Региональные/построчные "Название - число единица" сканируем ПЕРВЫМИ (но
    # добавляем в results в конце функции), чтобы застолбить их значения в
    # seen_vals с пометкой kind="part" раньше общего паттерна 1. Иначе общий
    # паттерн 1 (которому не важен префикс "Регион -") матчит те же самые числа
    # первым, помечает их kind="value" и они начинают выглядеть как отдельные
    # "итоговые" показатели наравне с настоящим общим итогом — из-за чего
    # _build_chart_data не может отличить "итог" от "часть разбивки".
    regional_results = []
    for m in re.finditer(regional_pattern, text, re.IGNORECASE | re.MULTILINE):
        label = _trim_label(m.group(1).strip().rstrip(" \t-–—"), max_len=55)
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
        regional_results.append({
            "value": val,
            "unit":  unit.strip(),
            "label": label,
            "trend": "neutral",
            "kind": "part",
        })

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

        # Убираем дубликаты по значению (в т.ч. уже застолблённые regional_pattern)
        key = f"{val}{unit}"
        if key in seen_vals:
            continue
        seen_vals.add(key)

        # Ищем метку — фраза перед числом (последнее предложение)
        start = max(0, m.start() - 120)
        snippet = text[start:m.start()].strip()
        parts = re.split(r'[.!?\n]', snippet)
        label = _trim_label(parts[-1].strip().lstrip(" ,;:—"))

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
                # "value" — агрегированный/общий показатель (итог, рост в %,
                # главная цифра из заголовка). "part" — сравнимая составляющая
                # разбивки (регион, возрастная группа и т.п.). Используется
                # в _build_chart_data, чтобы не смешивать итог с его частями
                # на одном графике.
                "kind": "value",
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
        label = _trim_label(parts[-1].strip().lstrip(" ,;:—"))
        trend = "neutral"
        ctx_before = text[max(0, m.start()-80):m.start()].lower()
        if re.search(r'вырос|увелич|прирост|рост|повыс|больше', ctx_before):
            trend = "up"
        results.append({"value": val, "unit": unit, "label": label or "Показатель", "trend": trend, "kind": "value"})

    # Региональные результаты добавляем в конец — застолблены в seen_vals выше,
    # поэтому общий паттерн 1 их уже не продублирует.
    results.extend(regional_results)

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
        val = re.sub(r'[ \t ]', '', m.group(1))
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
        label = _trim_label(parts[-1].strip().lstrip(" ,;:—-"))
        trend = "neutral"
        ctx_before = text[max(0, m.start() - 80):m.start()].lower()
        if re.search(r'вырос|увелич|прирост|рост|повыс|больше', ctx_before):
            trend = "up"
        elif re.search(r'снизил|уменьш|сократил|упал|меньше|снижен', ctx_before):
            trend = "down"
        results.append({"value": val, "unit": unit, "label": label or "Показатель", "trend": trend, "kind": "value"})
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
        results.append({"value": val, "unit": unit, "label": label[:55], "trend": "neutral", "kind": "part"})
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

    # Если в группе одновременно есть "part" (сравнимые между собой составляющие —
    # регионы, возрастные группы и т.п.) и "value" (агрегированный итог, темп роста,
    # главная цифра из заголовка) — для графика оставляем только "part". Иначе итог
    # попадает на диаграмму как будто это ещё один регион и визуально забивает
    # реальное сравнение, вводя в заблуждение (итог — это сумма частей, а не
    # отдельная сравнимая категория).
    parts_only = [s for s in best if s.get("kind") == "part"]
    if parts_only:
        best = parts_only

    # Раньше здесь был запасной вариант "если ни в одной группе нет >=2
    # сравнимых по единице измерения значений — берём любые 8 чисел подряд".
    # Это давало графики, где вперемешку оказывались триллионы сумов, проценты
    # и штуки предприятий — визуально бессмысленное сравнение разных величин.
    # Теперь: нет хотя бы двух чисел с ОДИНАКОВОЙ единицей — графика не строим
    # вовсе (site_builder аккуратно скрывает блок графика при пустом chart_data).
    result = best[:8] if len(best) >= 2 else []

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

    # Резервные экстракторы — на случай единиц, которых нет в основном списке
    # (человек, граждан, предприятий, ремесленников и т.п.).
    # Работают только по body (не по заголовку) — заголовок часто пересказывает
    # то же число другими словами и иначе "перебивает" реальную единицу измерения.
    if len(key_stats) < 4:
        seen_vals = {s["value"] for s in key_stats}
        # _extract_dash_items идёт ПЕРВЫМ: формат "Метка - число единица" структурно
        # однозначен (это всегда сравнимая часть разбивки, kind="part"), тогда как
        # _extract_grouped_counts — более общий паттерн "число единица" без метки-
        # разделителя, который не может отличить часть разбивки от отдельного
        # итога и поэтому всегда помечает kind="value". Если запустить его первым,
        # он "застолбит" числа из той же построчной разбивки (например,
        # "Таджикистан - 19 096 человек" при числах с разделителем разрядов) как
        # value, и часть строк разбивки в графике окажется рядом с настоящим
        # итогом как будто это два разных типа данных.
        for extra in _extract_dash_items(body) + _extract_grouped_counts(body):
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
                        "kind": "part",
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
