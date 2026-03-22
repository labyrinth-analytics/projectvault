"""
SQL Query Analyzer - Free tier pattern detection for SQL anti-patterns.
Supports T-SQL (SQL Server), MySQL, PostgreSQL, and SQLite.
ASCII-only: no Unicode characters in this file.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    severity: str       # "high", "medium", "low"
    category: str       # "performance", "correctness", "readability"
    pattern: str        # short slug
    description: str    # what the problem is
    why_it_matters: str # impact explanation
    hint: str           # direction for fix (no full rewrite -- that is premium)
    line_hint: Optional[str] = None  # relevant snippet from query


@dataclass
class AnalysisResult:
    issues: List[Issue] = field(default_factory=list)
    quick_wins: List[str] = field(default_factory=list)
    readability_notes: List[str] = field(default_factory=list)
    dialect_detected: str = "unknown"

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "low")


def detect_dialect(sql: str) -> str:
    """Best-effort dialect detection from SQL syntax clues."""
    sql_upper = sql.upper()
    if re.search(r'\bTOP\s+\d+\b', sql_upper) or re.search(r'\bNOLOCK\b', sql_upper):
        return "tsql"
    # MySQL: AUTO_INCREMENT can appear without LIMIT (e.g. CREATE TABLE)
    if re.search(r'\bAUTO_INCREMENT\b', sql_upper):
        return "mysql"
    if re.search(r'\bSERIAL\b|\bRETURNING\b', sql_upper):
        return "postgresql"
    if re.search(r'\bLIMIT\s+\d+\b', sql_upper):
        return "sqlite"
    # Default to T-SQL since most users are SQL Server
    return "tsql"


def normalize(sql: str) -> str:
    """Normalize whitespace and strip comments for pattern matching."""
    # Remove single-line comments
    sql = re.sub(r'--[^\n]*', ' ', sql)
    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)
    # Collapse whitespace
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql


def analyze(sql: str, dialect: Optional[str] = None) -> AnalysisResult:
    """
    Analyze a SQL query for common anti-patterns and issues.
    Returns an AnalysisResult with structured findings.
    This is the free-tier analysis -- no full rewrites.
    """
    result = AnalysisResult()
    clean = normalize(sql)
    upper = clean.upper()

    result.dialect_detected = dialect or detect_dialect(sql)

    # ------------------------------------------------------------------
    # Performance Issues
    # ------------------------------------------------------------------

    # SELECT *
    if re.search(r'\bSELECT\s+\*', upper):
        result.issues.append(Issue(
            severity="medium",
            category="performance",
            pattern="select_star",
            description="SELECT * retrieves all columns including those you do not need.",
            why_it_matters=(
                "Fetching unused columns wastes I/O, memory, and network bandwidth. "
                "It also prevents the optimizer from using covering indexes."
            ),
            hint="Replace SELECT * with an explicit list of only the columns your application uses.",
            line_hint="SELECT *"
        ))

    # Function on indexed column (e.g., YEAR(), MONTH(), UPPER(), LOWER(), CAST on column)
    func_on_col = re.findall(
        r'\b(YEAR|MONTH|DAY|DATEPART|UPPER|LOWER|CAST|CONVERT|LEN|ISNULL|COALESCE)\s*\(\s*\w+',
        upper
    )
    if func_on_col:
        funcs = list(set(func_on_col))
        result.issues.append(Issue(
            severity="high",
            category="performance",
            pattern="function_on_column",
            description=(
                "Function(s) applied directly to column(s) in WHERE/JOIN: "
                + ", ".join(funcs)
            ),
            why_it_matters=(
                "Wrapping a column in a function prevents the optimizer from using "
                "an index on that column. Every row must be scanned and the function "
                "evaluated -- this can turn a millisecond index seek into a full table scan."
            ),
            hint=(
                "Rewrite the condition to isolate the column. For example, instead of "
                "YEAR(OrderDate) = 2025, use OrderDate >= '2025-01-01' AND OrderDate < '2026-01-01'."
            )
        ))

    # Leading wildcard LIKE '%value'
    if re.search(r"LIKE\s+'%[^%]", upper) or re.search(r"LIKE\s+N'%[^%]", upper):
        result.issues.append(Issue(
            severity="high",
            category="performance",
            pattern="leading_wildcard",
            description="LIKE pattern starts with a wildcard ('%value'), forcing a full scan.",
            why_it_matters=(
                "A leading wildcard disables index seeks entirely. The engine must scan "
                "every row to find matches. On large tables this is catastrophically slow."
            ),
            hint=(
                "If possible, anchor the pattern on the left ('value%'). "
                "For full-text needs, consider a Full-Text Index (SQL Server) or "
                "a dedicated search engine."
            )
        ))

    # Correlated subquery (SELECT in WHERE/AND/OR condition)
    # Column may be qualified (e.g. o.Status), handle both WHERE and AND/OR positions
    correlated = re.findall(
        r'(?:WHERE|AND|OR)\s+(?:\w+\.)?\w+\s+IN\s*\(\s*SELECT\b',
        upper
    )
    if correlated:
        result.issues.append(Issue(
            severity="medium",
            category="performance",
            pattern="subquery_in_in",
            description="IN (SELECT ...) subquery found -- may be a correlated subquery.",
            why_it_matters=(
                "Correlated subqueries re-execute for every row of the outer query. "
                "A JOIN or EXISTS often allows the optimizer to find a much cheaper plan."
            ),
            hint=(
                "Consider rewriting as a JOIN or EXISTS clause. "
                "EXISTS is often faster when you only need to check existence, not retrieve values."
            )
        ))

    # OR in WHERE (can prevent index usage in some engines)
    if re.search(r'\bWHERE\b.*\bOR\b', upper):
        result.issues.append(Issue(
            severity="low",
            category="performance",
            pattern="or_in_where",
            description="OR condition in WHERE clause detected.",
            why_it_matters=(
                "OR conditions can prevent the optimizer from using a single index efficiently. "
                "In SQL Server, this sometimes produces an index scan instead of a seek."
            ),
            hint=(
                "Consider rewriting with UNION ALL (one branch per OR condition) "
                "to allow each branch to use its own index. Test with execution plans to confirm benefit."
            )
        ))

    # UNION (without ALL) -- eliminates duplicates via sort
    if re.search(r'\bUNION\b(?!\s+ALL)', upper):
        result.issues.append(Issue(
            severity="medium",
            category="performance",
            pattern="union_without_all",
            description="UNION without ALL performs a sort/distinct operation to remove duplicates.",
            why_it_matters=(
                "UNION sorts the entire result set to deduplicate, adding significant overhead. "
                "If you know the result sets cannot overlap, UNION ALL is much faster."
            ),
            hint="Replace UNION with UNION ALL if duplicate rows are not a concern.",
        ))

    # DISTINCT used (possible symptom of bad join)
    if re.search(r'\bSELECT\s+DISTINCT\b', upper):
        result.issues.append(Issue(
            severity="low",
            category="performance",
            pattern="select_distinct",
            description="SELECT DISTINCT found -- this forces a sort/deduplication pass.",
            why_it_matters=(
                "DISTINCT is sometimes used to mask a fan-out caused by a JOIN that "
                "produces duplicate rows. Fixing the JOIN is usually faster than paying "
                "the deduplication cost on every query."
            ),
            hint=(
                "Verify that JOIN conditions are correct and not producing unintended duplicates. "
                "If the JOIN is correct, DISTINCT is fine but be aware of the cost."
            )
        ))

    # Missing TOP / LIMIT (unbounded result set risk)
    has_top = bool(re.search(r'\bTOP\s+\d+\b', upper))
    has_limit = bool(re.search(r'\bLIMIT\s+\d+\b', upper))
    has_select = bool(re.search(r'\bSELECT\b', upper))
    has_aggregate = bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', upper))
    has_group_by = bool(re.search(r'\bGROUP\s+BY\b', upper))

    if has_select and not has_top and not has_limit and not has_aggregate and not has_group_by:
        result.issues.append(Issue(
            severity="low",
            category="performance",
            pattern="unbounded_result",
            description="No TOP/LIMIT clause -- query may return an unbounded number of rows.",
            why_it_matters=(
                "Without a row limit, a growing table can cause this query to return "
                "millions of rows, overwhelming the application and consuming excessive memory."
            ),
            hint=(
                "Add TOP N (T-SQL) or LIMIT N (MySQL/PostgreSQL) if your use case only "
                "needs a bounded result set. For reporting queries this may be intentional."
            )
        ))

    # Implicit type conversion risk (mixing types in JOIN/WHERE)
    if re.search(r"WHERE\s+\w+\s*=\s*'\d+|WHERE\s+\w+\s*=\s*\d+\s*AND\s*\w+\s+LIKE", upper):
        result.issues.append(Issue(
            severity="medium",
            category="correctness",
            pattern="implicit_conversion",
            description="Possible implicit type conversion in WHERE/JOIN condition.",
            why_it_matters=(
                "Comparing a numeric column to a string literal (or vice versa) forces "
                "the engine to cast every value, preventing index usage and sometimes "
                "producing wrong results due to collation or numeric overflow."
            ),
            hint="Ensure comparison operands are the same data type. Avoid mixing '123' (string) and 123 (int)."
        ))

    # ------------------------------------------------------------------
    # Readability Notes
    # ------------------------------------------------------------------

    # No table aliases on multi-table query
    table_count = len(re.findall(r'\b(FROM|JOIN)\b', upper))
    alias_count = len(re.findall(r'\b(FROM|JOIN)\b\s+\w+\s+\w+\b', upper))
    if table_count >= 2 and alias_count == 0:
        result.readability_notes.append(
            "Consider adding short aliases to tables (e.g., FROM Orders o JOIN Customers c) "
            "to improve readability and reduce ambiguity."
        )

    # Deep nesting (subquery inside subquery)
    paren_depth = 0
    max_depth = 0
    for ch in clean:
        if ch == '(':
            paren_depth += 1
            max_depth = max(max_depth, paren_depth)
        elif ch == ')':
            paren_depth -= 1
    if max_depth >= 3:
        result.readability_notes.append(
            "Query has deeply nested subqueries (depth " + str(max_depth) + "). "
            "Consider refactoring with CTEs (WITH ... AS (...)) for clarity."
        )

    # Long query without CTEs (rough proxy: > 300 chars, multiple subqueries)
    if len(clean) > 300 and clean.upper().count('SELECT') > 2 and 'WITH ' not in upper:
        result.readability_notes.append(
            "Complex query with multiple subqueries but no CTEs. "
            "CTEs (WITH ... AS (...)) can significantly improve readability and debuggability."
        )

    # ------------------------------------------------------------------
    # Quick Wins
    # ------------------------------------------------------------------

    if any(i.pattern == "select_star" for i in result.issues):
        result.quick_wins.append(
            "Replace SELECT * with explicit column names -- this is a 1-minute fix with measurable impact."
        )
    if any(i.pattern == "union_without_all" for i in result.issues):
        result.quick_wins.append(
            "Change UNION to UNION ALL if duplicates are not a concern -- zero-risk performance gain."
        )
    if any(i.pattern == "unbounded_result" for i in result.issues):
        result.quick_wins.append(
            "Add TOP 1000 (or appropriate N) to bound the result set during development."
        )

    return result


def format_report(result: AnalysisResult, query_preview: str = "") -> str:
    """
    Format an AnalysisResult as a human-readable text report.
    Uses ASCII-only characters.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("SQL QUERY ANALYSIS REPORT")
    lines.append("Dialect: " + result.dialect_detected.upper())
    if query_preview:
        preview = query_preview[:80].replace('\n', ' ')
        lines.append("Query: " + preview + ("..." if len(query_preview) > 80 else ""))
    lines.append("=" * 60)

    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 30)
    if result.issue_count == 0:
        lines.append("[OK] No issues detected.")
    else:
        lines.append(
            "Issues found: "
            + str(result.issue_count)
            + " ("
            + str(result.high_count) + " high, "
            + str(result.medium_count) + " medium, "
            + str(result.low_count) + " low)"
        )

    if result.issues:
        lines.append("")
        lines.append("ISSUES")
        lines.append("-" * 30)
        for idx, issue in enumerate(result.issues, 1):
            lines.append(
                str(idx) + ". [" + issue.severity.upper() + "] " + issue.pattern
            )
            lines.append("   What: " + issue.description)
            lines.append("   Why:  " + issue.why_it_matters)
            lines.append("   Hint: " + issue.hint)
            if issue.line_hint:
                lines.append("   In:   " + issue.line_hint)
            lines.append("")

    if result.quick_wins:
        lines.append("QUICK WINS")
        lines.append("-" * 30)
        for win in result.quick_wins:
            lines.append("  * " + win)
        lines.append("")

    if result.readability_notes:
        lines.append("READABILITY SUGGESTIONS")
        lines.append("-" * 30)
        for note in result.readability_notes:
            lines.append("  * " + note)
        lines.append("")

    lines.append("=" * 60)
    lines.append("FREE TIER ANALYSIS")
    lines.append("For a full optimized rewrite with index recommendations,")
    lines.append("get a premium API key at https://sqloptimizer.ronagent.com")
    lines.append("=" * 60)

    return '\n'.join(lines)
