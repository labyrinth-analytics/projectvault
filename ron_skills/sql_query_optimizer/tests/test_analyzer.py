"""
Tests for SQL Query Analyzer (free tier).
Run with: python -m pytest tests/ -v
ASCII-only characters only.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from analyzer import analyze, detect_dialect, format_report, Issue, AnalysisResult


# ------------------------------------------------------------------
# Dialect Detection
# ------------------------------------------------------------------

class TestDialectDetection:
    def test_tsql_top_keyword(self):
        sql = "SELECT TOP 10 * FROM Orders"
        assert detect_dialect(sql) == "tsql"

    def test_tsql_nolock(self):
        sql = "SELECT * FROM Orders WITH (NOLOCK)"
        assert detect_dialect(sql) == "tsql"

    def test_postgresql_returning(self):
        sql = "INSERT INTO Orders (col) VALUES (1) RETURNING id"
        assert detect_dialect(sql) == "postgresql"

    def test_mysql_auto_increment(self):
        sql = "CREATE TABLE t (id INT AUTO_INCREMENT)"
        assert detect_dialect(sql) == "mysql"

    def test_sqlite_limit(self):
        sql = "SELECT * FROM t LIMIT 10"
        # No MySQL-specific keywords, defaults to sqlite
        assert detect_dialect(sql) == "sqlite"

    def test_default_tsql(self):
        sql = "SELECT id FROM Orders WHERE id = 1"
        assert detect_dialect(sql) == "tsql"


# ------------------------------------------------------------------
# SELECT * Detection
# ------------------------------------------------------------------

class TestSelectStar:
    def test_detects_select_star(self):
        sql = "SELECT * FROM Orders"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "select_star" in patterns

    def test_no_false_positive_explicit_columns(self):
        sql = "SELECT id, name FROM Orders"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "select_star" not in patterns

    def test_select_star_severity_medium(self):
        sql = "SELECT * FROM Orders"
        result = analyze(sql)
        issue = next(i for i in result.issues if i.pattern == "select_star")
        assert issue.severity == "medium"


# ------------------------------------------------------------------
# Function on Column
# ------------------------------------------------------------------

class TestFunctionOnColumn:
    def test_year_function(self):
        sql = "SELECT id FROM Orders WHERE YEAR(OrderDate) = 2025"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "function_on_column" in patterns

    def test_upper_function(self):
        sql = "SELECT id FROM Customers WHERE UPPER(LastName) = 'SMITH'"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "function_on_column" in patterns

    def test_cast_function(self):
        sql = "SELECT id FROM Orders WHERE CAST(OrderID AS VARCHAR) = '123'"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "function_on_column" in patterns

    def test_severity_high(self):
        sql = "SELECT id FROM Orders WHERE YEAR(OrderDate) = 2025"
        result = analyze(sql)
        issue = next(i for i in result.issues if i.pattern == "function_on_column")
        assert issue.severity == "high"


# ------------------------------------------------------------------
# Leading Wildcard
# ------------------------------------------------------------------

class TestLeadingWildcard:
    def test_leading_percent(self):
        sql = "SELECT * FROM Products WHERE Name LIKE '%widget'"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "leading_wildcard" in patterns

    def test_trailing_percent_no_flag(self):
        sql = "SELECT * FROM Products WHERE Name LIKE 'widget%'"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "leading_wildcard" not in patterns

    def test_leading_wildcard_severity_high(self):
        sql = "SELECT id FROM Products WHERE Name LIKE '%widget'"
        result = analyze(sql)
        issue = next(i for i in result.issues if i.pattern == "leading_wildcard")
        assert issue.severity == "high"


# ------------------------------------------------------------------
# Subquery in IN
# ------------------------------------------------------------------

class TestSubqueryInIn:
    def test_in_subquery(self):
        sql = """
        SELECT * FROM Orders o
        WHERE o.Status IN (SELECT Status FROM StatusLookup WHERE IsActive = 1)
        """
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "subquery_in_in" in patterns

    def test_in_literal_list_no_flag(self):
        sql = "SELECT * FROM Orders WHERE Status IN ('Active', 'Pending')"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "subquery_in_in" not in patterns


# ------------------------------------------------------------------
# UNION without ALL
# ------------------------------------------------------------------

class TestUnion:
    def test_union_without_all(self):
        sql = "SELECT id FROM A UNION SELECT id FROM B"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "union_without_all" in patterns

    def test_union_all_no_flag(self):
        sql = "SELECT id FROM A UNION ALL SELECT id FROM B"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "union_without_all" not in patterns


# ------------------------------------------------------------------
# SELECT DISTINCT
# ------------------------------------------------------------------

class TestSelectDistinct:
    def test_detects_distinct(self):
        sql = "SELECT DISTINCT CustomerID FROM Orders"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "select_distinct" in patterns

    def test_no_distinct_no_flag(self):
        sql = "SELECT CustomerID FROM Orders"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "select_distinct" not in patterns


# ------------------------------------------------------------------
# Unbounded Result Set
# ------------------------------------------------------------------

class TestUnboundedResult:
    def test_missing_limit(self):
        sql = "SELECT id, name FROM Customers WHERE active = 1"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "unbounded_result" in patterns

    def test_top_suppresses_flag_tsql(self):
        sql = "SELECT TOP 100 id FROM Customers"
        result = analyze(sql, dialect="tsql")
        patterns = [i.pattern for i in result.issues]
        assert "unbounded_result" not in patterns

    def test_limit_suppresses_flag(self):
        sql = "SELECT id FROM customers LIMIT 100"
        result = analyze(sql, dialect="postgresql")
        patterns = [i.pattern for i in result.issues]
        assert "unbounded_result" not in patterns

    def test_aggregate_suppresses_flag(self):
        sql = "SELECT COUNT(*) FROM Orders"
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "unbounded_result" not in patterns


# ------------------------------------------------------------------
# Combined / Realistic Query
# ------------------------------------------------------------------

class TestRealisticQuery:
    def test_multi_issue_query(self):
        """The example query from the SKILL.md should generate multiple issues."""
        sql = """
        SELECT * FROM Orders o
        JOIN Customers c ON o.CustomerID = c.CustomerID
        WHERE YEAR(o.OrderDate) = 2025
        AND o.Status IN (SELECT Status FROM StatusLookup WHERE IsActive = 1)
        """
        result = analyze(sql)
        patterns = [i.pattern for i in result.issues]
        assert "select_star" in patterns
        assert "function_on_column" in patterns
        assert "subquery_in_in" in patterns
        assert result.high_count >= 1
        assert result.issue_count >= 3

    def test_clean_query_has_few_issues(self):
        """A well-written query should have zero or minimal issues."""
        sql = """
        SELECT TOP 100 o.OrderID, o.OrderDate, c.CustomerName
        FROM Orders o
        JOIN Customers c ON o.CustomerID = c.CustomerID
        WHERE o.OrderDate >= '2025-01-01' AND o.OrderDate < '2026-01-01'
        ORDER BY o.OrderDate DESC
        """
        result = analyze(sql, dialect="tsql")
        # Should find no more than 1 low-severity issue (the OR check won't fire)
        high_medium = [i for i in result.issues if i.severity in ("high", "medium")]
        assert len(high_medium) == 0


# ------------------------------------------------------------------
# Report Formatting
# ------------------------------------------------------------------

class TestFormatReport:
    def test_report_is_string(self):
        result = analyze("SELECT * FROM Orders")
        report = format_report(result, "SELECT * FROM Orders")
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_summary(self):
        result = analyze("SELECT * FROM Orders")
        report = format_report(result)
        assert "SUMMARY" in report

    def test_report_ok_when_no_issues(self):
        result = AnalysisResult()
        report = format_report(result)
        assert "[OK]" in report

    def test_report_ascii_only(self):
        result = analyze("SELECT * FROM Orders WHERE YEAR(d) = 2025")
        report = format_report(result)
        for ch in report:
            assert ord(ch) < 128, "Non-ASCII character found: " + repr(ch)


# ------------------------------------------------------------------
# AnalysisResult Properties
# ------------------------------------------------------------------

class TestAnalysisResultProperties:
    def test_counts(self):
        result = AnalysisResult()
        result.issues = [
            Issue("high", "performance", "p1", "d", "w", "h"),
            Issue("high", "performance", "p2", "d", "w", "h"),
            Issue("medium", "performance", "p3", "d", "w", "h"),
            Issue("low", "performance", "p4", "d", "w", "h"),
        ]
        assert result.issue_count == 4
        assert result.high_count == 2
        assert result.medium_count == 1
        assert result.low_count == 1

    def test_empty_result(self):
        result = AnalysisResult()
        assert result.issue_count == 0
        assert result.high_count == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
