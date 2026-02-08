# Health ClawKit 🐾

Personal health analytics dashboard that imports Apple Health data into DuckDB and visualizes trends.

---

## Getting Started

This project is designed to be set up by your AI agent (e.g., via [OpenClaw](https://openclaw.ai)). Point your agent to the `agent-instructions/` folder and they'll handle the rest:

1. **`agent-instructions/database_setup.md`** — Initialize the database and configure paths
2. **`agent-instructions/health_data_import.md`** — Set up daily automatic import of Apple Health data
3. **`agent-instructions/nutrition_logging.md`** — Enable meal logging with nutritional tracking

**Quick start:** Tell your agent: *"Clone this repo and follow the setup instructions in `agent-instructions/`."*

You'll need:
- A Mac with iCloud Drive
- The [Health Auto Export](https://apps.apple.com/app/health-auto-export/id1115567069) iOS app (Premium, for automated exports)
- An AI agent with shell access (OpenClaw, etc.)

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Apple Watch /  │────▶│   Apple Health   │────▶│ Health Auto     │
│  Body Scale /   │     │   (HealthKit)    │     │ Export App      │
│  iPhone Sensors │     │                  │     │ (iOS)           │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │ iCloud Drive    │
                                                │ CSV Exports     │
                                                └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │ Daily Import    │
                                                │ (Cron Job)      │
                                                └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │ DuckDB          │
                                                │ (Analytics DB)  │
                                                └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │ Dashboard       │
                                                │ (FastAPI+ECharts)│
                                                └─────────────────┘
```

---

## Features

- **Automated Import**: Reads Health Auto Export CSV files from iCloud Drive
- **Analytics Database**: DuckDB with long/normalized schema for flexible queries
- **Dashboard**: FastAPI backend + ECharts frontend, iOS Health app styling
- **Data Quality**: Built-in validation checks for anomaly detection
- **Nutrition Logging**: Track meals, macros, and micronutrients (work in progress)

### Why This Stack?

| Decision | Rationale |
|----------|-----------|
| **Health Auto Export app** | Apple doesn't expose HealthKit via REST API. This app auto-syncs 100+ metrics to iCloud with no manual intervention. |
| **iCloud Drive** | Privacy-first: data stays in Apple's ecosystem, no third-party routing. |
| **DuckDB** | Column-oriented analytics DB. Optimized for aggregations (trends, averages). Single file, zero config. |
| **Long/normalized schema** | CSV has 124 columns, mostly sparse. Normalized schema = flexible, extensible, efficient. |
| **FastAPI + ECharts** | Lightweight, fast, iOS Health app aesthetic. |

---

## Setup

### Prerequisites

- **Python 3.10+**
- **iOS device** with Health Auto Export app ([App Store](https://apps.apple.com/app/health-auto-export/id1115567069))
- **iCloud Drive** configured on your Mac

### 1. Clone and Configure

```bash
git clone <repo_url> health-clawkit
cd health-clawkit

# Create config from template
cp config.example.yaml config.yaml

# Edit config.yaml with your paths:
# - db_path: Where to store the DuckDB database
# - log_dir: Where to store import logs
# - icloud_folder: Path to Health Auto Export CSV folder
```

### 2. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python src/init_db.py
```

This creates the database with three tables:
- `readings`: Main fact table for all health metrics
- `metrics`: Metadata catalog
- `imports`: Import log for idempotency

### 4. Import Historical Data

```bash
# Import a specific CSV
python src/import_healthkit.py "/path/to/HealthMetrics-2026-02-05.csv"

# Or use the daily import script (scans iCloud folder for new files)
python src/daily_import.py
```

### 5. Start Dashboard

```bash
cd dashboard
python -m uvicorn main:app --host 0.0.0.0 --port 3000
```

Open http://localhost:3000 in your browser.

#### Run as a persistent service (macOS)

To keep the dashboard running across reboots, install it as a launchd service:

**Important:** Replace all `/path/to/` placeholders with your actual paths before loading!

```bash
cat > ~/Library/LaunchAgents/com.health-clawkit.dashboard.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.health-clawkit.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/health-clawkit/.venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>3000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/health-clawkit/dashboard</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/logs/dashboard-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/logs/dashboard-stderr.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.health-clawkit.dashboard.plist
```

The dashboard will then be available at `http://<your-machine-ip>:3000` from any device on your network.

To manage the service:
```bash
# Restart
launchctl kickstart -k gui/$(id -u)/com.health-clawkit.dashboard

# Stop
launchctl unload ~/Library/LaunchAgents/com.health-clawkit.dashboard.plist

# View logs
tail -f /path/to/logs/dashboard-stderr.log
```

---

## Configuration

The `config.yaml` file controls data paths:

```yaml
owner: Your Name

display:
  units: metric  # metric | imperial

data:
  db_path: /absolute/path/to/health.duckdb
  log_dir: /absolute/path/to/logs
  icloud_folder: /Users/you/Library/Mobile Documents/com~apple~CloudDocs/Health Data
```

**Note**: `config.yaml` is gitignored. Share `config.example.yaml` with others.

---

## Setting Up Health Auto Export (iOS)

1. Install **Health Auto Export** from the App Store (Premium required for automation)
2. Open app → **Automations** tab
3. Configure export:
   - **Format**: CSV
   - **Destination**: iCloud Drive
   - **Folder**: Choose/create a folder (e.g., "Health Data")
   - **Metrics**: Select all desired metrics (100+ available)
   - **Schedule**: Daily at 3:00 AM (or preferred time)
   - **Filename**: `HealthMetrics-YYYY-MM-DD.csv`
4. Enable **Background App Refresh** in iOS Settings
5. Test: Tap "Export Now" to verify files appear in iCloud Drive

---

## Daily Automation

Set up a cron job to run the import daily:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 6am):
0 6 * * * cd /path/to/health-clawkit && /path/to/.venv/bin/python src/daily_import.py >> /path/to/logs/cron.log 2>&1
```

The import script is idempotent (safe to run multiple times).

---

## Project Structure

```
health-clawkit/
├── config.yaml          # Your config (gitignored)
├── config.example.yaml  # Template for new installs
├── .gitignore
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── agent-instructions/  # Setup guides for AI agents
│   ├── database_setup.md
│   ├── health_data_import.md
│   ├── nutrition_logging.md
│   └── schema_and_queries.md  # DB schema + example queries
├── scripts/
│   ├── process_meal_photos.sh  # Batch resize meal photos
│   └── resize_image.sh         # Single image resize
├── src/
│   ├── config.py        # Shared config loader
│   ├── daily_import.py  # Scan iCloud folder, import new CSVs
│   ├── import_healthkit.py  # Transform CSV → DuckDB
│   ├── init_db.py       # Initialize database schema
│   ├── init_nutrition.py    # Initialize nutrition_log table
│   ├── log_nutrition.py     # Log nutrition entry
│   ├── nutrition_summary.py # Generate nutrition summaries
│   └── validate.py      # Data quality checks
└── dashboard/
    ├── main.py          # FastAPI backend
    └── static/
        ├── index.html   # Dashboard UI
        ├── detail.html  # Detailed metric view
        ├── app.js       # Frontend logic
        └── styles.css   # iOS Health-inspired styles
```

---

## Available Scripts

### Import & Validation

```bash
# Import a single CSV
python src/import_healthkit.py "/path/to/file.csv"

# Daily import (scans iCloud folder for new files)
python src/daily_import.py
python src/daily_import.py --dry-run  # Preview without importing

# Run data quality checks
python src/validate.py
python src/validate.py --verbose
```

### Nutrition (Experimental)

```bash
# Initialize nutrition_log table
python src/init_nutrition.py

# Log a meal (JSON input)
python src/log_nutrition.py --json '{"meal_time":"2026-02-07T12:30:00",...}'

# View daily summary
python src/nutrition_summary.py --today
python src/nutrition_summary.py --date 2026-02-07
```

### Dashboard

```bash
cd dashboard
python -m uvicorn main:app --port 3000 --reload
```

---

## Data Available

The platform tracks 100+ metrics from Apple Health, including:

**Activity**: Steps, flights climbed, distance, active energy, exercise minutes  
**Heart**: Resting HR, walking HR, HRV, VO₂ max, recovery  
**Sleep**: Total sleep, REM, deep, core, time in bed  
**Body**: Weight, BMI, body fat %, lean mass  
**Vitals**: Blood pressure, oxygen saturation, respiratory rate  
**Mindfulness**: Meditation minutes  
**Nutrition**: (Manual logging via scripts, not from Apple Health)

---

## Privacy Notes

- Health data is sensitive — configure paths carefully
- `config.yaml` is gitignored to prevent accidental sharing of personal paths
- Consider encrypting the DuckDB file if storing on cloud storage
- The dashboard has no authentication — run locally only

---

## Contributing

This is a personal project, but suggestions are welcome!

1. Fork the repo
2. Create a feature branch
3. Make your changes (update docs if needed)
4. Submit a pull request

---

## License

MIT License - see LICENSE file for details

---

*Last updated: 2026-02-07*
