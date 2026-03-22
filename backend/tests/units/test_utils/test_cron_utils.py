"""Tests for app.utils.cron_utils."""

from app.utils.cron_utils import check_conflicts, parse_cron_to_apscheduler, validate_cron


class TestParseCronToApscheduler:
    def test_daily_expression(self):
        result = parse_cron_to_apscheduler("10 22 * * *")
        assert result == {
            "minute": "10",
            "hour": "22",
            "day": "*",
            "month": "*",
            "day_of_week": "*",
        }

    def test_monthly_expression(self):
        result = parse_cron_to_apscheduler("55 8 1 * *")
        assert result == {
            "minute": "55",
            "hour": "8",
            "day": "1",
            "month": "*",
            "day_of_week": "*",
        }


class TestValidateCron:
    def test_valid_daily(self):
        assert validate_cron("10 22 * * *") is True

    def test_valid_midnight(self):
        assert validate_cron("0 3 * * *") is True

    def test_invalid_string(self):
        assert validate_cron("invalid") is False

    def test_invalid_values(self):
        assert validate_cron("99 25 * * *") is False


class TestCheckConflicts:
    def test_same_expression_conflicts(self):
        assert check_conflicts("0 3 * * *", ["0 3 * * *"]) is True

    def test_different_expression_no_conflict(self):
        assert check_conflicts("0 3 * * *", ["10 22 * * *"]) is False

    def test_empty_other_expressions(self):
        assert check_conflicts("0 3 * * *", []) is False
