import pytest
from app.services.sql_safety import SQLValidationError, validate_and_sanitize_sql


def test_valid_select_query():
    sql = "SELECT server_id, server_name FROM servers WHERE region = 'us-east';"
    sanitized = validate_and_sanitize_sql(sql)
    assert "SELECT" in sanitized
    assert "LIMIT 1000" in sanitized


def test_forbidden_drop_table():
    sql = "DROP TABLE servers;"
    with pytest.raises(SQLValidationError):
        validate_and_sanitize_sql(sql)


def test_forbidden_delete_statement():
    sql = "DELETE FROM members WHERE user_id = '123';"
    with pytest.raises(SQLValidationError):
        validate_and_sanitize_sql(sql)


def test_forbidden_update_statement():
    sql = "UPDATE servers SET server_name = 'Hacked';"
    with pytest.raises(SQLValidationError):
        validate_and_sanitize_sql(sql)


def test_multiple_statements_rejection():
    sql = "SELECT * FROM servers; DROP TABLE channels;"
    with pytest.raises(SQLValidationError):
        validate_and_sanitize_sql(sql)


def test_cte_with_statement():
    sql = "WITH active_servers AS (SELECT server_id FROM daily_stats WHERE total_messages > 100) SELECT * FROM active_servers;"
    sanitized = validate_and_sanitize_sql(sql)
    assert "WITH" in sanitized
    assert "LIMIT 1000" in sanitized
