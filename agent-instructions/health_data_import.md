# Health Data Import (Cron Setup)

You're setting up a daily cron job to automatically import new Apple Health CSV exports into the database. This should run after you've completed `database_setup.md`.

## Prerequisites

1. Database initialized (see `database_setup.md`)
2. `config.yaml` configured with correct `icloud_folder` path
3. Your human has Health Auto Export running on their iOS device, syncing CSVs to iCloud Drive

## Setup

### 1. Test the import manually first

```bash
cd <project-dir>

# Dry run — shows what would be imported without changing anything
.venv/bin/python src/daily_import.py --dry-run

# If that looks right, do a real import
.venv/bin/python src/daily_import.py
```

You should see:
- Config loaded successfully
- Database found at the configured path
- iCloud folder scanned
- Import summary (files found, rows imported)

### 2. Set up the cron job

```bash
crontab -e
```

Add this line (runs daily at 6:00 AM):

```
0 6 * * * cd <project-dir> && <project-dir>/.venv/bin/python src/daily_import.py >> <log-dir>/cron.log 2>&1
```

Replace:
- `<project-dir>` — absolute path to the cloned `health-clawkit` directory
- `<log-dir>` — the `log_dir` path from `config.yaml`

### Example

If the project is at `/Users/lilliana/Projects/health-clawkit` and logs go to `/Users/lilliana/data/health/logs`:

```
0 6 * * * cd /Users/lilliana/Projects/health-clawkit && /Users/lilliana/Projects/health-clawkit/.venv/bin/python src/daily_import.py >> /Users/lilliana/data/health/logs/cron.log 2>&1
```

## How it works

1. The script reads `config.yaml` for the database path and iCloud folder
2. Scans the iCloud folder for CSV files
3. Checks the `imports` table to see which files have already been processed
4. Imports only new files (idempotent — safe to run multiple times)
5. Appends output to `cron.log`

## Verify after first cron run

```bash
tail -f <log-dir>/cron.log
```

Look for successful import messages with row counts.

## Troubleshooting

**"config.yaml not found"** — The `cd <project-dir>` in the cron command is essential. The script looks for `config.yaml` relative to the working directory.

**"No module named yaml"** — The cron is using system Python instead of the virtualenv. Make sure you're using the full absolute path to `.venv/bin/python`.

**No new files imported** — Check that Health Auto Export is running on your human's iOS device and syncing to the correct iCloud folder.

**Permission errors** — On macOS, cron may need Full Disk Access. Go to System Settings → Privacy & Security → Full Disk Access and add `/usr/sbin/cron`.
