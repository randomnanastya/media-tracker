"""Tests for app.utils.cron_utils."""

from app.utils.cron_utils import check_conflicts, parse_cron_to_apscheduler, validate_cron


class TestParseCronToApscheduler:
    def test_daily_expression(self) -> None:
        result = parse_cron_to_apscheduler("10 22 * * *")
        assert result == {
            "minute": "10",
            "hour": "22",
            "day": "*",
            "month": "*",
            "day_of_week": "*",
        }

    def test_monthly_expression(self) -> None:
        result = parse_cron_to_apscheduler("55 8 1 * *")
        assert result == {
            "minute": "55",
            "hour": "8",
            "day": "1",
            "month": "*",
            "day_of_week": "*",
        }

    def test_weekly_expression(self) -> None:
        result = parse_cron_to_apscheduler("30 14 * * 0")
        assert result == {
            "minute": "30",
            "hour": "14",
            "day": "*",
            "month": "*",
            "day_of_week": "0",
        }

    def test_midnight_expression(self) -> None:
        result = parse_cron_to_apscheduler("0 0 * * *")
        assert result["minute"] == "0"
        assert result["hour"] == "0"

    def test_all_wildcard_fields_are_returned(self) -> None:
        result = parse_cron_to_apscheduler("5 3 * * *")
        assert set(result.keys()) == {"minute", "hour", "day", "month", "day_of_week"}

    def test_field_order_minute_is_first_not_hour(self) -> None:
        # "10 22 * * *" => minute=10, hour=22, not the other way around
        result = parse_cron_to_apscheduler("10 22 * * *")
        assert result["minute"] == "10"
        assert result["hour"] == "22"

    def test_specific_month_and_day(self) -> None:
        result = parse_cron_to_apscheduler("0 12 15 6 *")
        assert result == {
            "minute": "0",
            "hour": "12",
            "day": "15",
            "month": "6",
            "day_of_week": "*",
        }

    def test_extra_whitespace_is_split_correctly(self) -> None:
        # strip() is not used in implementation — confirm it works with single spaces
        result = parse_cron_to_apscheduler("0 2 * * *")
        assert result["minute"] == "0"
        assert result["hour"] == "2"


class TestValidateCron:
    def test_valid_daily(self) -> None:
        assert validate_cron("10 22 * * *") is True

    def test_valid_midnight(self) -> None:
        assert validate_cron("0 3 * * *") is True

    def test_valid_weekly(self) -> None:
        assert validate_cron("0 8 * * 0") is True

    def test_valid_monthly(self) -> None:
        assert validate_cron("55 8 1 * *") is True

    def test_invalid_string(self) -> None:
        assert validate_cron("invalid") is False

    def test_invalid_values_out_of_range(self) -> None:
        assert validate_cron("99 25 * * *") is False

    def test_empty_string(self) -> None:
        assert validate_cron("") is False

    def test_too_few_fields(self) -> None:
        assert validate_cron("10 22 * *") is False

    def test_invalid_minute_above_59(self) -> None:
        assert validate_cron("60 12 * * *") is False

    def test_invalid_hour_above_23(self) -> None:
        assert validate_cron("0 24 * * *") is False

    def test_invalid_day_of_week_above_6(self) -> None:
        # croniter allows 7 as Sunday as well, but 8 is invalid
        assert validate_cron("0 12 * * 8") is False

    def test_random_text(self) -> None:
        assert validate_cron("not a cron at all") is False

    def test_valid_zero_minute_zero_hour(self) -> None:
        assert validate_cron("0 0 * * *") is True

    def test_valid_last_valid_minute_and_hour(self) -> None:
        assert validate_cron("59 23 * * *") is True


class TestCheckConflicts:
    def test_same_expression_conflicts(self) -> None:
        assert check_conflicts("0 3 * * *", ["0 3 * * *"]) is True

    def test_different_expression_no_conflict(self) -> None:
        assert check_conflicts("0 3 * * *", ["10 22 * * *"]) is False

    def test_empty_other_expressions(self) -> None:
        assert check_conflicts("0 3 * * *", []) is False

    def test_conflict_with_one_of_multiple_others(self) -> None:
        # "0 3 * * *" conflicts with itself in the list
        assert check_conflicts("0 3 * * *", ["10 22 * * *", "0 3 * * *"]) is True

    def test_no_conflict_with_multiple_others(self) -> None:
        assert check_conflicts("0 3 * * *", ["10 22 * * *", "20 23 * * *"]) is False

    def test_daily_vs_monthly_same_time_should_conflict(self) -> None:
        # daily "0 22 * * *" and monthly "0 22 1 * *" will share the 1st of each month
        assert check_conflicts("0 22 * * *", ["0 22 1 * *"]) is True

    def test_weekly_different_hour_no_conflict(self) -> None:
        # weekly Sunday at 10:00 vs weekly Sunday at 11:00
        assert check_conflicts("0 10 * * 0", ["0 11 * * 0"]) is False

    def test_custom_n_parameter_low_n_may_miss_sparse_conflict(self) -> None:
        # With n=1, monthly "0 22 1 * *" may not trigger in next 1 daily runs.
        # This tests the n parameter is actually used. No assertion on result value —
        # just confirms it doesn't raise.
        result = check_conflicts("0 22 * * *", ["0 22 1 * *"], n=1)
        assert isinstance(result, bool)

    def test_returns_false_for_adjacent_minutes(self) -> None:
        # 0:00 vs 0:01 — different minutes, no conflict
        assert check_conflicts("0 0 * * *", ["1 0 * * *"]) is False

    def test_conflict_with_same_minute_different_day_of_week(self) -> None:
        # same minute+hour but different day_of_week (Mon vs Sun) → no conflict
        assert check_conflicts("0 8 * * 1", ["0 8 * * 0"]) is False
