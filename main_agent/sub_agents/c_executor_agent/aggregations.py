# # ==============================
# # aggregations.py
# # Aggregation layer for Agent C
# # ==============================

# import re
# from dataclasses import dataclass
# from typing import List, Optional, Sequence, Dict


# TIME_COL = "event_time"
# METRIC_COL = "total_events"

# # Columns that are allowed to appear in filter clauses (WHERE)
# FILTERABLE_COLUMNS = {
#     "event_time",
#     "hr",
#     "is_engaged_view",
#     "is_retargeting",
#     "media_source",
#     "partner",
#     "app_id",
#     "site_id",
#     "engagement_type",
# }

# # Any filterable column is also groupable
# GROUPABLE_COLUMNS = set(FILTERABLE_COLUMNS)


# @dataclass
# class AggregationSpec:
#     """
#     Defines how to aggregate a base SQL query.

#     group_by: columns to group by (e.g., ["partner"] or ["media_source", "is_retargeting"])
#     metric_alias: alias for the aggregated metric column
#     top_n: if provided, return only top N by metric (ORDER BY DESC LIMIT N)
#     add_percent: if True, add percent_of_total column
#     time_granularity: optional; only used if group_by includes event_time.
#         One of: "hour", "day", "month".
#         Does not add/normalize time filters; only changes grouping.
#     """
#     group_by: Sequence[str]
#     metric_alias: str = "clicks"
#     top_n: Optional[int] = None
#     add_percent: bool = False
#     time_granularity: Optional[str] = None  # "hour" | "day" | "month"


# def ensure_at_least_one_filter_present(sql: str) -> None:
#     """
#     Enforces the A/B contract:
#     Do not aggregate (or execute) SQL unless it contains at least one WHERE filter
#     on one of the FILTERABLE_COLUMNS. Time filters are NOT mandatory.
#     """
#     if "where" not in sql.lower():
#         raise ValueError("SQL must include at least one filter (WHERE clause).")

#     col_pattern = r"|".join([re.escape(c) for c in FILTERABLE_COLUMNS])

#     has_filter = bool(
#         re.search(
#             rf"\b({col_pattern})\b\s*(=|!=|<>|>=|>|<=|<|between\b|in\b|like\b|is\b)",
#             sql,
#             re.IGNORECASE
#         )
#     )

#     if not has_filter:
#         raise ValueError(
#             f"SQL must include at least one filter on one of: {sorted(FILTERABLE_COLUMNS)}"
#         )


# def _validate_group_by(cols: Sequence[str]) -> List[str]:
#     """Validate group-by columns."""
#     cols_l = [c.strip() for c in cols if c and c.strip()]
#     unknown = [c for c in cols_l if c not in GROUPABLE_COLUMNS]

#     if unknown:
#         raise ValueError(f"Unknown/ungroupable columns: {unknown}")

#     return cols_l


# def _apply_time_granularity(col: str, granularity: Optional[str]) -> str:
#     """
#     If grouping by event_time and granularity is provided,
#     generate a truncated time expression for grouping.
#     """
#     if col != TIME_COL or not granularity:
#         return col

#     g = granularity.lower()
#     if g == "hour":
#         return f"TIMESTAMP_TRUNC({TIME_COL}, HOUR) AS {TIME_COL}"
#     if g == "day":
#         return f"DATE({TIME_COL}) AS {TIME_COL}"
#     if g == "month":
#         return f"DATE_TRUNC(DATE({TIME_COL}), MONTH) AS {TIME_COL}"

#     raise ValueError("time_granularity must be one of: hour/day/month")


# def build_aggregated_sql(
#     base_sql: str,
#     spec: AggregationSpec,
#     metric_col: str = METRIC_COL,
# ) -> str:
#     """
#     Wraps base_sql as a subquery and aggregates it according to spec.
#     The only enforced precondition is: base_sql must include at least one filter
#     on FILTERABLE_COLUMNS.
#     """
#     ensure_at_least_one_filter_present(base_sql)
#     group_cols = _validate_group_by(spec.group_by)

#     subquery = f"({base_sql}) AS base"

#     select_group_parts = []
#     group_by_parts = []

#     for c in group_cols:
#         select_expr = _apply_time_granularity(c, spec.time_granularity)
#         select_group_parts.append(select_expr)

#         if c == TIME_COL and spec.time_granularity:
#             group_by_parts.append(TIME_COL)
#         else:
#             group_by_parts.append(c)

#     metric_expr = f"SUM({metric_col}) AS {spec.metric_alias}"
#     select_list = ",\n  ".join(select_group_parts + [metric_expr])

#     sql = f"""
# SELECT
#   {select_list}
# FROM {subquery}
# GROUP BY {", ".join(group_by_parts)}
# """.strip()

#     if spec.add_percent:
#         sql = f"""
# WITH agg AS (
#   {sql}
# )
# SELECT
#   *,
#   SAFE_DIVIDE({spec.metric_alias}, SUM({spec.metric_alias}) OVER()) * 100 AS percent_of_total
# FROM agg
# """.strip()

#     if spec.top_n:
#         sql = f"""
# {sql}
# ORDER BY {spec.metric_alias} DESC
# LIMIT {int(spec.top_n)}
# """.strip()

#     return sql


# # Convenience group-by functions for each column

# def group_by_partner(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["partner"], **kwargs))

# def group_by_media_source(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["media_source"], **kwargs))

# def group_by_app_id(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["app_id"], **kwargs))

# def group_by_site_id(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["site_id"], **kwargs))

# def group_by_engagement_type(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["engagement_type"], **kwargs))

# def group_by_is_retargeting(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["is_retargeting"], **kwargs))

# def group_by_is_engaged_view(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["is_engaged_view"], **kwargs))

# def group_by_hr(base_sql: str, **kwargs) -> str:
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=["hr"], **kwargs))

# def group_by_event_time(base_sql: str, granularity: str = "day", **kwargs) -> str:
#     return build_aggregated_sql(
#         base_sql,
#         AggregationSpec(group_by=["event_time"], time_granularity=granularity, **kwargs),
#     )

# def group_by_any(base_sql: str, columns: Sequence[str], **kwargs) -> str:
#     """Generic group-by for any valid combination of columns."""
#     return build_aggregated_sql(base_sql, AggregationSpec(group_by=list(columns), **kwargs))


# def build_multi_aggregations(
#     base_sql: str,
#     specs: Sequence[AggregationSpec],
# ) -> Dict[str, str]:
#     """Build multiple aggregate SQL queries from the same base SQL."""
#     out = {}
#     for i, spec in enumerate(specs, start=1):
#         key = f"agg_{i}_{'_'.join(spec.group_by)}"
#         out[key] = build_aggregated_sql(base_sql, spec)
#     return out

# ==============================
# aggregations.py
# Aggregation layer for Agent C
# ==============================

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Dict


TIME_COL = "event_time"
METRIC_COL = "total_events"

# Columns that are allowed to appear in filter clauses (WHERE)
FILTERABLE_COLUMNS = {
    "event_time",
    "hr",
    "is_engaged_view",
    "is_retargeting",
    "media_source",
    "partner",
    "app_id",
    "site_id",
    "engagement_type",
}

# Any filterable column is also groupable
GROUPABLE_COLUMNS = set(FILTERABLE_COLUMNS)


@dataclass
class AggregationSpec:
    """
    Defines how to aggregate a base SQL query.

    group_by: columns to group by (e.g., ["partner"] or ["media_source", "is_retargeting"])
    metric_alias: alias for the aggregated metric column
    top_n: if provided, return only top N by metric (ORDER BY DESC LIMIT N)
    add_percent: if True, add percent_of_total column
    time_granularity: optional; only used if group_by includes event_time.
        One of: "hour", "day", "month".
        Does not add/normalize time filters; only changes grouping.
    """
    group_by: Sequence[str]
    metric_alias: str = "clicks"
    top_n: Optional[int] = None
    add_percent: bool = False
    time_granularity: Optional[str] = None  # "hour" | "day" | "month"


def ensure_at_least_one_filter_present(sql: str) -> None:
    """
    Enforces the A/B contract:
    Do not aggregate (or execute) SQL unless it contains at least one WHERE filter
    on one of the FILTERABLE_COLUMNS. Time filters are NOT mandatory.
    Handles function-wrapped columns like DATE(event_time).
    """
    if "where" not in sql.lower():
        raise ValueError("SQL must include at least one filter (WHERE clause).")

    col_pattern = r"|".join([re.escape(c) for c in FILTERABLE_COLUMNS])

    # Pattern 1: Direct column usage (e.g., app_id = "...")
    # Pattern 2: Function-wrapped columns (e.g., DATE(event_time) = "...")
    has_filter = bool(
        re.search(
            rf"\b({col_pattern})\b\s*(=|!=|<>|>=|>|<=|<|between\b|in\b|like\b|is\b)",
            sql,
            re.IGNORECASE
        )
        or re.search(
            rf"\b\w+\s*\(\s*({col_pattern})\s*\)\s*(=|!=|<>|>=|>|<=|<|between\b|in\b|like\b|is\b)",
            sql,
            re.IGNORECASE
        )
    )

    if not has_filter:
        raise ValueError(
            f"SQL must include at least one filter on one of: {sorted(FILTERABLE_COLUMNS)}"
        )


def _validate_group_by(cols: Sequence[str]) -> List[str]:
    """Validate group-by columns."""
    cols_l = [c.strip() for c in cols if c and c.strip()]
    unknown = [c for c in cols_l if c not in GROUPABLE_COLUMNS]

    if unknown:
        raise ValueError(f"Unknown/ungroupable columns: {unknown}")

    return cols_l


def _apply_time_granularity(col: str, granularity: Optional[str]) -> str:
    """
    If grouping by event_time and granularity is provided,
    generate a truncated time expression for grouping.
    """
    if col != TIME_COL or not granularity:
        return col

    g = granularity.lower()
    if g == "hour":
        return f"TIMESTAMP_TRUNC({TIME_COL}, HOUR) AS {TIME_COL}"
    if g == "day":
        return f"DATE({TIME_COL}) AS {TIME_COL}"
    if g == "month":
        return f"DATE_TRUNC(DATE({TIME_COL}), MONTH) AS {TIME_COL}"

    raise ValueError("time_granularity must be one of: hour/day/month")


def build_aggregated_sql(
    base_sql: str,
    spec: AggregationSpec,
    metric_col: str = METRIC_COL,
) -> str:
    """
    Wraps base_sql as a subquery and aggregates it according to spec.
    Precondition: base_sql must include at least one filter on FILTERABLE_COLUMNS.
    Supports empty group_by => total only (single-row aggregation).
    """
    ensure_at_least_one_filter_present(base_sql)

    group_cols = _validate_group_by(spec.group_by or [])

    subquery = f"({base_sql}) AS base"

    # ----- Case: TOTAL only (no group_by) -----
    if len(group_cols) == 0:
        base_agg = f"""
SELECT
  SUM({metric_col}) AS {spec.metric_alias}
FROM {subquery}
""".strip()

        if spec.add_percent:
            base_agg = f"""
WITH agg AS (
  {base_agg}
)
SELECT
  *,
  SAFE_DIVIDE({spec.metric_alias}, SUM({spec.metric_alias}) OVER()) * 100 AS percent_of_total
FROM agg
""".strip()

        # top_n is irrelevant here; single row anyway
        return base_agg

    # ----- Regular GROUP BY case -----
    select_group_parts = []
    group_by_parts = []

    for c in group_cols:
        select_expr = _apply_time_granularity(c, spec.time_granularity)
        select_group_parts.append(select_expr)

        if c == TIME_COL and spec.time_granularity:
            group_by_parts.append(TIME_COL)
        else:
            group_by_parts.append(c)

    metric_expr = f"SUM({metric_col}) AS {spec.metric_alias}"
    select_list = ",\n  ".join(select_group_parts + [metric_expr])

    sql = f"""
SELECT
  {select_list}
FROM {subquery}
GROUP BY {", ".join(group_by_parts)}
""".strip()

    if spec.add_percent:
        sql = f"""
WITH agg AS (
  {sql}
)
SELECT
  *,
  SAFE_DIVIDE({spec.metric_alias}, SUM({spec.metric_alias}) OVER()) * 100 AS percent_of_total
FROM agg
""".strip()

    if spec.top_n:
        sql = f"""
{sql}
ORDER BY {spec.metric_alias} DESC
LIMIT {int(spec.top_n)}
""".strip()

    return sql


# Convenience group-by functions for each column

def group_by_partner(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["partner"], **kwargs))

def group_by_media_source(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["media_source"], **kwargs))

def group_by_app_id(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["app_id"], **kwargs))

def group_by_site_id(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["site_id"], **kwargs))

def group_by_engagement_type(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["engagement_type"], **kwargs))

def group_by_is_retargeting(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["is_retargeting"], **kwargs))

def group_by_is_engaged_view(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["is_engaged_view"], **kwargs))

def group_by_hr(base_sql: str, **kwargs) -> str:
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=["hr"], **kwargs))

def group_by_event_time(base_sql: str, granularity: str = "day", **kwargs) -> str:
    return build_aggregated_sql(
        base_sql,
        AggregationSpec(group_by=["event_time"], time_granularity=granularity, **kwargs),
    )

def group_by_any(base_sql: str, columns: Sequence[str], **kwargs) -> str:
    """Generic group-by for any valid combination of columns."""
    return build_aggregated_sql(base_sql, AggregationSpec(group_by=list(columns), **kwargs))


def build_multi_aggregations(
    base_sql: str,
    specs: Sequence[AggregationSpec],
) -> Dict[str, str]:
    """Build multiple aggregate SQL queries from the same base SQL."""
    out = {}
    for i, spec in enumerate(specs, start=1):
        key = f"agg_{i}_{'_'.join(spec.group_by or [])}"
        out[key] = build_aggregated_sql(base_sql, spec)
    return out

