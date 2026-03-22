from datetime import UTC, datetime

from croniter import croniter  # type: ignore[import-untyped]


def parse_cron_to_apscheduler(cron_expr: str) -> dict[str, str]:
    parts = cron_expr.split()
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def validate_cron(cron_expr: str) -> bool:
    return bool(croniter.is_valid(cron_expr))


def check_conflicts(cron_expr: str, other_expressions: list[str], n: int = 30) -> bool:
    now = datetime.now(UTC)
    it = croniter(cron_expr, now)
    target_runs = {it.get_next(datetime).replace(second=0, microsecond=0) for _ in range(n)}

    for expr in other_expressions:
        other_it = croniter(expr, now)
        for _ in range(n):
            run_time = other_it.get_next(datetime).replace(second=0, microsecond=0)
            if run_time in target_runs:
                return True
    return False
