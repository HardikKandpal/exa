import logging
import re

import sqlglot
from app.config import settings
from sqlglot import exp

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", r"\bALTER\b",
    r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b", r"\bEXEC\b",
    r"\bEXECUTE\b", r"\bPG_SLEEP\b", r"\bCOPY\b", r"\bINTO\b", r"\bEXPLAIN\b",
    r"\bCALL\b", r"\bDO\b", r"\bVACUUM\b"
]


class SQLValidationError(Exception):
    pass


def validate_and_sanitize_sql(sql_query: str, max_limit: int = settings.MAX_SQL_ROW_LIMIT) -> str:
    """
    Validates that a given SQL string is a safe, single SELECT or CTE query.
    Enforces row bounds and rejects prohibited statements.
    """
    cleaned_sql = sql_query.strip().rstrip(";")

    # 1. Regex pre-filter for forbidden DDL / DML / System keywords
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise SQLValidationError(f"Forbidden SQL operation detected matching pattern: {pattern}")

    # 2. Check for multiple statements separated by semicolon
    if ";" in cleaned_sql:
        raise SQLValidationError("Multiple SQL statements in a single query are not allowed.")

    # 3. Parse AST using sqlglot
    try:
        parsed_expressions = sqlglot.parse(cleaned_sql, read="postgres")
    except Exception as e:
        raise SQLValidationError(f"SQL Syntax Error during parsing: {str(e)}")

    if not parsed_expressions or len(parsed_expressions) != 1:
        raise SQLValidationError("Only a single SQL statement is allowed.")

    expression = parsed_expressions[0]
    if expression is None:
        raise SQLValidationError("Failed to parse SQL query.")

    # 4. Enforce that statement is a SELECT or CTE WITH expression
    if not isinstance(expression, (exp.Select, exp.Union)):
        raise SQLValidationError(f"Only SELECT queries are permitted. Got: {expression.key.upper()}")

    # 5. Row bound enforcement (Inject LIMIT if not present or exceeds max_limit)
    limit_node = expression.find(exp.Limit)
    if limit_node is None:
        cleaned_sql = f"{cleaned_sql} LIMIT {max_limit}"
    else:
        try:
            current_limit = int(limit_node.expression.this)
            if current_limit > max_limit:
                limit_node.args["expression"] = exp.Literal.number(max_limit)
                cleaned_sql = expression.sql(dialect="postgres")
        except Exception:
            pass

    return cleaned_sql
