"""
Configuration module for query limits and execution parameters.

Controls LIMIT clauses and row limits across agents.
Adjust these values based on your data volume, memory constraints, and performance needs.
"""

# ============================================
# Intent Agent Configuration
# ============================================
# Default LIMIT for general non-aggregated queries
# Increase this if you need more raw data, decrease for performance
QUERY_LIMIT_DEFAULT = 100000

# LIMIT for raw detail queries (when no aggregation)
# Applied when user asks for raw data without top-N aggregation
QUERY_LIMIT_RAW_DATA = 50000


# ============================================
# Executor Agent Configuration
# ============================================
# LIMIT clause added to SQL queries sent to BigQuery
# Prevents BigQuery buffer allocation errors on very large result sets
# Set higher if you have more memory/network bandwidth, lower for resource constraints
SQL_LIMIT_CLAUSE = 500000

# Maximum rows returned for non-aggregated queries
# This is the hard cap sent to the frontend (memory/UI performance limit)
MAX_ROWS_RETURNED = 100000

# Maximum rows returned for aggregated queries (top-N, group by, etc)
# Aggregated data is typically smaller, so we can return more rows
MAX_ROWS_AGGREGATED = 50000


# ============================================
# Recommendations for Tuning
# ============================================
# If your charts show truncated data:
# 1. Increase MAX_ROWS_RETURNED and MAX_ROWS_AGGREGATED
# 2. Increase SQL_LIMIT_CLAUSE if BigQuery is slow
# 3. Increase QUERY_LIMIT_RAW_DATA for more raw detail rows
#
# If performance is slow:
# 1. Decrease the above limits
# 2. Monitor logs for "[ExecutorAgent Config]" and "[IntentAgent Config]" to see current values
