# Database Setup

You're setting up the health platform database on your human's machine. Follow these steps in order.

## Prerequisites

1. Project cloned to a local directory
2. Python 3.10+ installed on the machine

## Steps

### 1. Create virtual environment and install dependencies

```bash
cd <project-dir>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and set paths appropriate for your human's machine:

- **`db_path`** — where to store the DuckDB database file (e.g., `~/data/health/health.duckdb`). Pick a location outside the project directory so health data doesn't end up in git.
- **`log_dir`** — where to store import/validation logs (e.g., `~/data/health/logs`)
- **`icloud_folder`** — path to the iCloud folder where Health Auto Export saves CSV files. Ask your human where this is if you're unsure — they need to have the Health Auto Export iOS app configured first.

The database file and log directory will be created automatically. The iCloud folder must already exist.

### 3. Initialize the health database

```bash
.venv/bin/python src/init_db.py
```

This creates three tables:
- **`readings`** — main fact table for all health metrics (timestamp, metric, value, unit)
- **`metrics`** — metadata catalog of available metrics
- **`imports`** — import log tracking which CSV files have been processed (for idempotency)

### 4. Initialize the nutrition table

If your human wants nutrition logging (recommended — see `nutrition_logging.md`):

```bash
.venv/bin/python src/init_nutrition.py
```

This adds:
- **`nutrition_log`** — meal entries with full macro/micro nutrient breakdown

### 5. Verify

```bash
# Check config is loading correctly
.venv/bin/python -c "from src.config import get_db_path; print('DB:', get_db_path())"

# Run validation (should pass with empty database)
.venv/bin/python src/validate.py --verbose
```

If both pass, you're good. Move on to `health_data_import.md` to set up the daily import cron.

## Database Schema

See `schema_and_queries.md` in this folder for full schema documentation and example queries.

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| **DuckDB** | Column-oriented analytics DB, optimized for aggregations. Single file, zero config. |
| **Long/normalized schema** | Health Auto Export CSVs have 124 columns, mostly sparse. Normalized = flexible and efficient. |
| **Idempotent imports** | The `imports` table tracks processed files. Safe to re-run imports without duplicating data. |

## Troubleshooting

**"config.yaml not found"** — Make sure you're running commands from the project root directory.

**"No module named yaml"** — You're using system Python instead of the virtualenv. Use `.venv/bin/python`.

**Database file not created** — Check that the parent directory of `db_path` exists. The script creates the file but not parent directories — create them yourself if needed.
