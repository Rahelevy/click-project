import re

# ------------------------------
# FIELD extractors
# ------------------------------

def extract_app_id(q: str):
    m = re.search(r"app(?:_id)? (\S+)", q)
    return m.group(1) if m else None

def extract_media_source(q: str):
    m = re.search(r"media[_ ]source (\S+)", q)
    return m.group(1) if m else None

def extract_partner(q: str):
    m = re.search(r"partner (\S+)", q)
    return m.group(1) if m else None

def extract_site_id(q: str):
    m = re.search(r"site[_ ]id (\S+)", q)
    return m.group(1) if m else None

def extract_engagement_type(q: str):
    m = re.search(r"engagement[_ ]type (\S+)", q)
    return m.group(1) if m else None

def extract_is_engaged_view(q: str):
    if "engaged view" in q or "video" in q:
        return True
    if "no engaged view" in q or "not engaged view" in q:
        return False
    return None

def extract_is_retargeting(q: str):
    if "retargeting" in q:
        return True
    if "no retargeting" in q:
        return False
    return None

def extract_date(q: str):
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", q)
    return m.group(1) if m else None

def extract_hour(q: str):
    m = re.search(r"\bat (\d{1,2}):\d{2}\b", q)
    return m.group(1) if m else None


# ------------------------------
# MAIN SQL BUILDER
# ------------------------------

def convert_question_to_sql(question: str) -> str:
    q = question.lower()

    # Count or list
    is_count = any(word in q for word in ["count", "how many", "number of"])
    select_clause = "COUNT(*) AS total" if is_count else "*"

    # Extract fields
    app_id = extract_app_id(q)
    media_source = extract_media_source(q)
    partner = extract_partner(q)
    site_id = extract_site_id(q)
    engagement_type = extract_engagement_type(q)
    is_engaged_view = extract_is_engaged_view(q)
    is_retargeting = extract_is_retargeting(q)
    date_filter = extract_date(q)
    hour_filter = extract_hour(q)

    # WHERE building
    where = []

    if app_id:
        where.append(f"app_id = '{app_id}'")
    if media_source:
        where.append(f"media_source = '{media_source}'")
    if partner:
        where.append(f"partner = '{partner}'")
    if site_id:
        where.append(f"site_id = '{site_id}'")
    if engagement_type:
        where.append(f"engagement_type = '{engagement_type}'")
    if is_engaged_view is not None:
        where.append(f"is_engaged_view = {str(is_engaged_view).upper()}")
    if is_retargeting is not None:
        where.append(f"is_retargeting = {str(is_retargeting).upper()}")
    if date_filter:
        where.append(f"DATE(event_time) = DATE('{date_filter}')")
    if hour_filter is not None:
        where.append(f"hr = '{hour_filter}'")

    where_sql = " AND ".join(where) if where else "1=1"

    # Final SQL
    sql = f"""
        SELECT {select_clause}
        FROM `practicode-2025.clicks_data_prac.encoded_clicks`
        WHERE {where_sql}
        LIMIT 500;
    """

    return sql.strip()