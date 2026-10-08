"""MySQL health metrics collection and threshold evaluation."""

import mysql.connector


def collect_health_metrics(config: dict) -> dict:
    mysql_config = config["mysql"]
    connection = mysql.connector.connect(
        host=mysql_config.get("host", "localhost"),
        port=int(mysql_config.get("port", 3306)),
        user=mysql_config["user"],
        password=mysql_config.get("password", ""),
        database=mysql_config.get("database"),
    )

    try:
        cursor = connection.cursor()
        metrics = {}

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected'")
        metrics["threads_connected"] = int(cursor.fetchone()[1])

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_running'")
        metrics["threads_running"] = int(cursor.fetchone()[1])

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Questions'")
        questions = int(cursor.fetchone()[1])

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime'")
        uptime = int(cursor.fetchone()[1])

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries'")
        metrics["slow_queries"] = int(cursor.fetchone()[1])

        metrics["questions"] = questions
        metrics["uptime_seconds"] = uptime
        metrics["queries_per_second"] = round(
            questions / uptime if uptime > 0 else 0.0, 4
        )
        return metrics
    finally:
        connection.close()


def evaluate_health(config: dict, metrics: dict) -> tuple[bool, list[str]]:
    thresholds = config.get("health", {}).get("thresholds", {})
    failures = []

    checks = {
        "threads_connected": ("max_threads_connected", "threads_connected"),
        "threads_running": ("max_threads_running", "threads_running"),
        "slow_queries": ("max_slow_queries", "slow_queries"),
        "queries_per_second": ("max_queries_per_second", "queries_per_second"),
    }

    for metric_name, (threshold_name, display_name) in checks.items():
        if threshold_name not in thresholds:
            continue

        limit = float(thresholds[threshold_name])
        value = float(metrics.get(metric_name, 0))

        if value > limit:
            failures.append(
                f"{display_name}={value} exceeds threshold {limit}"
            )

    return not failures, failures
