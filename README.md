# MySQL Backup Health Scheduler

A single Python application that:

- reads backup, health, email, and schedule settings from one YAML file
- creates daily MySQL backups with `mysqldump`
- monitors MySQL health metrics
- compares metrics with configurable thresholds
- sends SMTP email alerts when backup or health checks fail
- writes timestamped run reports
- can run once manually or continuously at a configured daily time

## Project structure

```text
mysql-backup-health-scheduler/
├── app.py
├── config.yaml
├── config_loader.py
├── backup.py
├── health.py
├── email_alert.py
├── scheduler.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── reports/
```

## Requirements

- Python 3.10+
- MySQL Server
- `mysqldump`
- A MySQL account with permission to read the target database
- SMTP server for real email alerts

## Installation

```bash
python -m pip install -r requirements.txt
```

Set the MySQL password in the environment instead of committing it:

### Git Bash

```bash
export MYSQL_PASSWORD='your_mysql_password'
```

Check the YAML configuration:

```bash
python -c "from config_loader import load_config; print(load_config('config.yaml')['mysql']['database'])"
```

## Run a backup and health check

```bash
python app.py --config config.yaml
```

The application creates:

```text
backups/
reports/
```

A successful run returns exit code `0`. A backup or health failure returns exit code `1`.

## Test health monitoring without creating a backup

```bash
python app.py --skip-backup
```

## Test email locally

The default example uses SMTP on `localhost:1025`, which is useful with a local SMTP test server. A simple server can be started with:

```bash
python -m smtpd -c DebuggingServer -n localhost:1025
```

If your Python installation does not include the legacy `smtpd` module, use any local SMTP debugging server and configure its host/port in `config.yaml`.

To force an alert for a demonstration, temporarily set a threshold very low, for example:

```yaml
health:
  thresholds:
    max_threads_connected: 0
    max_threads_running: 0
    max_slow_queries: 0
    max_queries_per_second: 0
```

Restore sensible thresholds after testing.

## Daily scheduler

Run once immediately:

```bash
python scheduler.py --config config.yaml --once
```

Run continuously:

```bash
python scheduler.py --config config.yaml
```

The scheduler reads:

```yaml
schedule:
  daily_time: "02:00"
```

and launches `app.py` once per day.

For production, Windows Task Scheduler or Linux cron can launch:

```bash
python scheduler.py --config config.yaml --once
```

at the desired time.

## Configuration

All main settings are in `config.yaml`:

- MySQL connection
- `mysqldump` executable path
- backup directory and retention
- health thresholds
- SMTP settings
- daily schedule
- report/log locations

Environment variables can be referenced using `${VARIABLE_NAME}`.

## Example output

```text
2026-10-08 21:00:00 | INFO | Starting MySQL backup and health check
2026-10-08 21:00:00 | INFO | Creating MySQL backup for database 'backup_restore_demo'
2026-10-08 21:00:01 | INFO | Backup completed successfully
2026-10-08 21:00:01 | INFO | All health metrics are within configured thresholds
2026-10-08 21:00:01 | INFO | Report written to reports/run_report_*.txt
```

## Safety

Never commit:

- real MySQL passwords
- SMTP passwords
- API keys
- private credentials

Use environment variables and keep `.env` files out of Git.

## Task mapping

| Requirement | Implementation |
|---|---|
| Parse YAML config | `config_loader.py` |
| Backup with subprocess + mysqldump | `backup.py` |
| Health metrics + thresholds | `health.py` |
| SMTP alerts | `email_alert.py` |
| Daily execution | `scheduler.py` |
| Single application entry point | `app.py` |
