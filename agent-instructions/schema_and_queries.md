# Database Schema & Query Reference

This is your reference for working with the health database. Use it when your human asks questions about their health data, or when you need to write custom queries.

## Schema Overview

The database uses a **long/normalized** schema. Instead of 124+ sparse columns, each reading is a single row with `(timestamp, metric, value, unit)`. This makes it flexible and efficient for analytics.

---

## Tables

### `readings`

Main fact table for all health metrics.

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | TIMESTAMP | When the reading was recorded |
| `metric` | VARCHAR | Metric name (e.g., "Heart Rate", "Weight") |
| `value` | DOUBLE | Numeric value |
| `unit` | VARCHAR | Unit of measurement (e.g., "bpm", "lb") |
| `source` | VARCHAR | Data source (e.g., "healthkit", "manual") |

**Primary Key:** `(timestamp, metric, source)`
**Indexes:** `idx_readings_timestamp`, `idx_readings_metric`

### `metrics`

Metadata catalog for all known metrics.

| Column | Type | Description |
|--------|------|-------------|
| `metric_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `name` | VARCHAR UNIQUE | Canonical metric name |
| `display_name` | VARCHAR | Human-friendly name |
| `category` | VARCHAR | Grouping (cardiovascular, sleep, activity, etc.) |
| `unit` | VARCHAR | Standard unit |
| `description` | VARCHAR | Optional notes |

### `imports`

Tracks which CSV files have been imported (for idempotency).

| Column | Type | Description |
|--------|------|-------------|
| `import_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `filename` | VARCHAR UNIQUE | Source filename |
| `imported_at` | TIMESTAMP | When import completed |
| `rows_added` | INTEGER | Number of readings added |
| `source` | VARCHAR | Data source type |

### `nutrition_log`

Meal-level nutrition tracking with full macro/micro breakdown.

| Column | Type | Description |
|--------|------|-------------|
| `entry_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `meal_time` | TIMESTAMP | When the meal was eaten |
| `meal_type` | VARCHAR | breakfast, lunch, dinner, snack |
| `meal_name` | VARCHAR | Short name |
| `meal_description` | TEXT | Detailed description |
| `food_items` | TEXT | JSON array of items with portions |
| `calories` | DOUBLE | Total calories |
| `protein_g` | DOUBLE | Protein |
| `carbs_g` | DOUBLE | Total carbohydrates |
| `fat_total_g` | DOUBLE | Total fat |
| `fat_saturated_g` | DOUBLE | Saturated fat |
| `fat_unsaturated_g` | DOUBLE | Unsaturated fat |
| `fat_trans_g` | DOUBLE | Trans fat |
| `fiber_g` | DOUBLE | Dietary fiber |
| `sugar_g` | DOUBLE | Sugars |
| `sodium_mg` | DOUBLE | Sodium |
| `potassium_mg` | DOUBLE | Potassium |
| `calcium_mg` | DOUBLE | Calcium |
| `iron_mg` | DOUBLE | Iron |
| `magnesium_mg` | DOUBLE | Magnesium |
| `vitamin_d_mcg` | DOUBLE | Vitamin D |
| `vitamin_b12_mcg` | DOUBLE | Vitamin B12 |
| `vitamin_c_mg` | DOUBLE | Vitamin C |
| `cholesterol_mg` | DOUBLE | Cholesterol |
| `source` | VARCHAR | chat, photo, imported |
| `logged_at` | TIMESTAMP | When entry was created |
| `notes` | TEXT | Additional notes |

---

## Useful Queries

Use these as starting points when your human asks about their health data. All queries run against DuckDB.

### Database overview

```sql
-- How much data do we have?
SELECT COUNT(*) as total_readings FROM readings;
SELECT COUNT(DISTINCT metric) as unique_metrics FROM readings;

-- Date range coverage
SELECT MIN(timestamp) as first, MAX(timestamp) as last,
       DATE_DIFF('day', MIN(timestamp), MAX(timestamp)) as days
FROM readings;

-- Top metrics by volume
SELECT metric, COUNT(*) as count FROM readings
GROUP BY metric ORDER BY count DESC LIMIT 10;
```

### Heart & cardiovascular

```sql
-- Resting heart rate trend
SELECT DATE(timestamp) as date, AVG(value) as resting_hr
FROM readings WHERE metric = 'Resting Heart Rate'
GROUP BY date ORDER BY date;

-- HRV trend
SELECT DATE(timestamp) as date, AVG(value) as avg_hrv
FROM readings WHERE metric = 'Heart Rate Variability'
GROUP BY date ORDER BY date;

-- Heart rate by day (with min/max)
SELECT DATE(timestamp) as date,
       AVG(value) as avg_hr, MIN(value) as min_hr, MAX(value) as max_hr
FROM readings WHERE metric LIKE 'Heart Rate%'
GROUP BY date ORDER BY date;
```

### Sleep

```sql
-- Sleep duration by night
SELECT DATE(timestamp) as night, value as sleep_hours
FROM readings WHERE metric = 'Sleep Analysis [Total]'
ORDER BY night DESC;

-- Sleep stages (most recent night)
SELECT metric, value as hours
FROM readings WHERE metric LIKE 'Sleep Analysis%'
  AND DATE(timestamp) = (
    SELECT MAX(DATE(timestamp)) FROM readings WHERE metric LIKE 'Sleep Analysis%'
  )
ORDER BY metric;
```

### Activity

```sql
-- Daily steps
SELECT DATE(timestamp) as date, SUM(value) as steps
FROM readings WHERE metric = 'Step Count'
GROUP BY date ORDER BY date DESC;

-- Daily active energy
SELECT DATE(timestamp) as date, SUM(value) as active_kcal
FROM readings WHERE metric = 'Active Energy'
GROUP BY date ORDER BY date DESC;

-- Exercise minutes
SELECT DATE(timestamp) as date, SUM(value) as exercise_min
FROM readings WHERE metric = 'Apple Exercise Time'
GROUP BY date ORDER BY date DESC;
```

### Body metrics

```sql
-- Weight trend
SELECT timestamp, value as weight, unit
FROM readings WHERE metric = 'Body Mass'
ORDER BY timestamp DESC;

-- Body fat
SELECT timestamp, value as body_fat_pct
FROM readings WHERE metric = 'Body Fat Percentage'
ORDER BY timestamp DESC;
```

### Nutrition

```sql
-- Today's meals
SELECT meal_time, meal_type, meal_name, calories, protein_g, carbs_g, fat_total_g
FROM nutrition_log WHERE DATE(meal_time) = CURRENT_DATE
ORDER BY meal_time;

-- Daily nutrition totals (last 7 days)
SELECT DATE(meal_time) as date,
       SUM(calories) as cals, SUM(protein_g) as protein,
       SUM(carbs_g) as carbs, SUM(fat_total_g) as fat
FROM nutrition_log
WHERE meal_time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date ORDER BY date;
```

### Data quality

```sql
-- Future timestamps (should be zero)
SELECT COUNT(*) FROM readings WHERE timestamp > NOW();

-- Suspiciously high values
SELECT metric, MAX(value) as max_val, unit FROM readings
GROUP BY metric, unit HAVING MAX(value) > 1000 ORDER BY max_val DESC;

-- Import history
SELECT filename, rows_added, imported_at FROM imports ORDER BY imported_at DESC;
```

---

## Design Notes

| Decision | Why |
|----------|-----|
| **Long format** | 124 sparse columns → compact rows. Adding new metrics = just new rows, no schema changes. |
| **DuckDB** | Columnar analytics DB. Fast aggregations, single file, zero config. |
| **Idempotent imports** | `imports` table tracks files. Safe to re-run without duplicating. |
| **Nutrition in wide format** | Meals naturally have all nutrients together. Simpler queries than normalizing each nutrient. |

## Adding New Data Sources

If your human gets a new health device or data source:
1. Write an import script that transforms the data into `(timestamp, metric, value, unit, source)` rows
2. Use the `source` column to distinguish provenance
3. Add new metrics to the `metrics` table if needed
4. Register imports in the `imports` table for idempotency
