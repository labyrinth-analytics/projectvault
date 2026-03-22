"""
SQL Query Optimizer MCP Server (FastMCP)
Free-tier: pattern analysis, readability suggestions, quick wins.
Premium-tier: full rewrite via API (requires SQL_OPTIMIZER_API_KEY).
ASCII-only: no Unicode characters in this file.
"""

import os
import json
import sys
import urllib.request
import urllib.error
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Import from same package directory
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze, format_report, detect_dialect

PREMIUM_API_URL = "https://api.sqloptimizer.ronagent.com/v1/optimize"

mcp = FastMCP("sql-query-optimizer")


@mcp.tool()
def analyze_query(sql: str, dialect: Optional[str] = None) -> str:
    """
    Analyze a SQL query for performance issues, anti-patterns, and readability problems.

    Free tier: pattern detection, severity ratings, fix hints, quick wins.
    No API key required.

    Args:
        sql: The SQL query to analyze.
        dialect: Database dialect. One of: tsql, mysql, postgresql, sqlite.
                 If not provided, dialect is auto-detected from the query syntax.

    Returns:
        A structured text report with all issues found, quick wins, and readability notes.
    """
    if not sql or not sql.strip():
        return "Error: No SQL query provided. Please pass a SQL statement to analyze."

    valid_dialects = {"tsql", "mysql", "postgresql", "sqlite"}
    if dialect and dialect.lower() not in valid_dialects:
        return (
            "Error: Unknown dialect '"
            + dialect
            + "'. Valid options: tsql, mysql, postgresql, sqlite."
        )

    result = analyze(sql, dialect=dialect.lower() if dialect else None)
    return format_report(result, query_preview=sql.strip())


@mcp.tool()
def get_anti_patterns() -> str:
    """
    List all SQL anti-patterns that this tool detects, with brief explanations.
    Useful for understanding what the analyzer checks before submitting a query.

    Returns:
        A formatted list of detected anti-patterns with severity and category.
    """
    patterns = [
        ("high",   "performance",   "function_on_column",
         "Function applied to a column in WHERE/JOIN (e.g., YEAR(col) = 2025) -- prevents index usage."),
        ("high",   "performance",   "leading_wildcard",
         "LIKE '%value' -- leading wildcard forces full table scan."),
        ("medium", "performance",   "select_star",
         "SELECT * -- fetches all columns, blocks covering indexes."),
        ("medium", "performance",   "subquery_in_in",
         "IN (SELECT ...) -- possible correlated subquery, consider JOIN or EXISTS."),
        ("medium", "performance",   "union_without_all",
         "UNION without ALL -- sorts entire result set to deduplicate."),
        ("medium", "correctness",   "implicit_conversion",
         "Mixing types in WHERE/JOIN (string vs numeric) -- may prevent index use."),
        ("low",    "performance",   "or_in_where",
         "OR in WHERE -- can prevent single-index utilization."),
        ("low",    "performance",   "select_distinct",
         "SELECT DISTINCT -- forces deduplication sort; sometimes masks a bad JOIN."),
        ("low",    "performance",   "unbounded_result",
         "No TOP/LIMIT -- query may return millions of rows on large tables."),
    ]

    lines = []
    lines.append("SQL ANTI-PATTERNS DETECTED BY THIS TOOL")
    lines.append("=" * 50)
    lines.append("")
    for severity, category, pattern, description in patterns:
        lines.append("[" + severity.upper() + "] " + pattern + " (" + category + ")")
        lines.append("  " + description)
        lines.append("")

    lines.append("Submit a query to analyze_query() to check for these patterns.")
    return '\n'.join(lines)


@mcp.tool()
def detect_query_dialect(sql: str) -> str:
    """
    Auto-detect the SQL dialect of a query (T-SQL, MySQL, PostgreSQL, SQLite).

    Args:
        sql: A SQL query string.

    Returns:
        The detected dialect string: tsql, mysql, postgresql, or sqlite.
    """
    if not sql or not sql.strip():
        return "Error: No SQL provided."
    dialect = detect_dialect(sql)
    return "Detected dialect: " + dialect


@mcp.tool()
def optimize_query(
    sql: str,
    dialect: Optional[str] = None,
    table_info: Optional[str] = None,
    database_engine: Optional[str] = None
) -> str:
    """
    Premium feature: get a full optimized rewrite of the SQL query.

    Requires SQL_OPTIMIZER_API_KEY environment variable.
    If the key is not set, returns the free-tier analysis with instructions
    to get a premium key.

    Args:
        sql: The SQL query to optimize.
        dialect: Database dialect: tsql, mysql, postgresql, sqlite.
        table_info: Optional schema/table info (column names, indexes, row counts).
        database_engine: Optional engine version (e.g., "SQL Server 2019", "MySQL 8.0").

    Returns:
        Full optimized rewrite with explanations (premium) or free analysis with upgrade prompt.
    """
    if not sql or not sql.strip():
        return "Error: No SQL query provided."

    api_key = os.environ.get("SQL_OPTIMIZER_API_KEY", "").strip()

    if not api_key:
        # Fall back to free analysis + upgrade prompt
        free_result = analyze(sql, dialect=dialect.lower() if dialect else None)
        report = format_report(free_result, query_preview=sql.strip())
        report += (
            "\n\n[PREMIUM UPGRADE]\n"
            "To get a full optimized rewrite with:\n"
            "  - Complete query rewrite with change-by-change explanations\n"
            "  - Specific CREATE INDEX recommendations\n"
            "  - Execution plan cost breakdown\n"
            "  - Dialect-specific tuning (" + (dialect or "T-SQL") + ")\n"
            "  - Before/after performance estimates\n"
            "\nGet a premium API key at: https://sqloptimizer.ronagent.com\n"
            "Then set: SQL_OPTIMIZER_API_KEY=<your-key>"
        )
        return report

    # Premium path: call the API
    payload = {
        "query": sql,
        "dialect": dialect or detect_dialect(sql),
        "context": {
            "table_info": table_info or "",
            "database_engine": database_engine or ""
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            PREMIUM_API_URL,
            data=data,
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return (
            "API error " + str(e.code) + ": " + e.reason + "\n"
            + (error_body[:500] if error_body else "")
        )
    except urllib.error.URLError as e:
        return "Network error calling optimizer API: " + str(e.reason)
    except json.JSONDecodeError:
        return "Error: Could not parse API response."

    # Format premium response
    lines = []
    lines.append("=" * 60)
    lines.append("SQL QUERY OPTIMIZER -- PREMIUM RESULTS")
    lines.append("=" * 60)
    lines.append("")

    if "optimized_query" in result:
        lines.append("OPTIMIZED QUERY")
        lines.append("-" * 30)
        lines.append(result["optimized_query"])
        lines.append("")

    if "changes" in result:
        lines.append("CHANGES MADE")
        lines.append("-" * 30)
        for change in result.get("changes", []):
            lines.append("  * " + str(change))
        lines.append("")

    if "index_recommendations" in result:
        lines.append("INDEX RECOMMENDATIONS")
        lines.append("-" * 30)
        for idx_rec in result.get("index_recommendations", []):
            lines.append("  " + str(idx_rec))
        lines.append("")

    if "execution_plan" in result:
        lines.append("EXECUTION PLAN NOTES")
        lines.append("-" * 30)
        lines.append(str(result["execution_plan"]))
        lines.append("")

    if "performance_estimate" in result:
        lines.append("PERFORMANCE ESTIMATE")
        lines.append("-" * 30)
        lines.append(str(result["performance_estimate"]))
        lines.append("")

    if not lines[4:]:
        # Fallback if API returns unexpected shape
        lines.append(json.dumps(result, indent=2))

    return '\n'.join(lines)


if __name__ == "__main__":
    mcp.run()
