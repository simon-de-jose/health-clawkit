"""Health Dashboard - FastAPI Backend"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import duckdb
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import get_db_path

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_PATH = str(get_db_path())

# iOS Health Color Palette
COLORS = {
    "activity": "#FF9500",  # Orange
    "heart": "#FF3B30",     # Red
    "sleep": "#5E5CE6",     # Purple/indigo
}


def get_sparkline_data(metric: str, days: int = 7) -> List[Dict]:
    """Get sparkline data (last 7 days)"""
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        if metric == "Step Count":
            result = conn.execute("""
                SELECT DATE(timestamp) as date, SUM(value) as value
                FROM readings 
                WHERE metric = 'Step Count' 
                AND timestamp > NOW() - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """).fetchall()
        elif metric == "Active Energy":
            result = conn.execute("""
                SELECT DATE(timestamp) as date, SUM(value) as value
                FROM readings 
                WHERE metric = 'Active Energy' 
                AND timestamp > NOW() - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """).fetchall()
        else:  # HRV, Resting HR
            result = conn.execute(f"""
                SELECT DATE(timestamp) as date, AVG(value) as value
                FROM readings 
                WHERE metric = '{metric}' 
                AND timestamp > NOW() - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """).fetchall()
        
        conn.close()
        return [{"date": str(r[0]), "value": float(r[1])} for r in result]
    except Exception as e:
        print(f"Error getting sparkline for {metric}: {e}")
        return []


@app.get("/")
async def read_root():
    """Serve index.html"""
    return FileResponse("static/index.html")


@app.get("/detail.html")
async def read_detail():
    """Serve detail.html"""
    return FileResponse("static/detail.html")


@app.get("/api/overview")
async def get_overview():
    """Get overview data for all 5 metrics"""
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        # Active Energy - Today's total
        result = conn.execute("""
            SELECT SUM(value) as total
            FROM readings 
            WHERE metric = 'Active Energy' 
            AND DATE(timestamp) = CURRENT_DATE
        """).fetchone()
        calories_value = int(result[0]) if result[0] else 0
        
        # Steps - Today's total
        result = conn.execute("""
            SELECT SUM(value) as total
            FROM readings 
            WHERE metric = 'Step Count' 
            AND DATE(timestamp) = CURRENT_DATE
        """).fetchone()
        steps_value = int(result[0]) if result[0] else 0
        
        # Resting HR - Latest
        result = conn.execute("""
            SELECT AVG(value) as avg_hr
            FROM readings 
            WHERE metric = 'Resting Heart Rate' 
            AND timestamp > NOW() - INTERVAL '7 days'
        """).fetchone()
        resting_hr_value = round(result[0], 1) if result[0] else 0.0
        
        # HRV - 7-day average
        result = conn.execute("""
            SELECT AVG(value) as avg_hrv
            FROM readings 
            WHERE metric = 'Heart Rate Variability' 
            AND timestamp > NOW() - INTERVAL '7 days'
        """).fetchone()
        hrv_value = round(result[0], 1) if result[0] else 0.0
        
        # Sleep - Latest
        result = conn.execute("""
            SELECT value
            FROM readings 
            WHERE metric = 'Sleep Analysis [Total]'
            ORDER BY timestamp DESC 
            LIMIT 1
        """).fetchone()
        sleep_total_hours = float(result[0]) if result and result[0] else 7.5
        sleep_hours = int(sleep_total_hours)
        sleep_minutes = int((sleep_total_hours - sleep_hours) * 60)
        
        # Sleep breakdown
        result = conn.execute("""
            SELECT 
                MAX(CASE WHEN metric = 'Sleep Analysis [Deep]' THEN value ELSE 0 END) as deep,
                MAX(CASE WHEN metric = 'Sleep Analysis [REM]' THEN value ELSE 0 END) as rem,
                MAX(CASE WHEN metric = 'Sleep Analysis [Core]' THEN value ELSE 0 END) as core
            FROM readings 
            WHERE metric LIKE 'Sleep Analysis%'
            AND timestamp = (SELECT MAX(timestamp) FROM readings WHERE metric LIKE 'Sleep Analysis%')
        """).fetchone()
        
        if result:
            sleep_deep = int(result[0] * 60) if result[0] else int(sleep_hours * 60 * 0.2)
            sleep_rem = int(result[1] * 60) if result[1] else int(sleep_hours * 60 * 0.25)
            sleep_core = int(result[2] * 60) if result[2] else int(sleep_hours * 60 * 0.55)
        else:
            sleep_deep = int(sleep_hours * 60 * 0.2)
            sleep_rem = int(sleep_hours * 60 * 0.25)
            sleep_core = int(sleep_hours * 60 * 0.55)
        
        conn.close()
        
        return JSONResponse({
            "energy": {
                "value": calories_value,
                "unit": "cal",
                "sparkline": get_sparkline_data("Active Energy")
            },
            "steps": {
                "value": steps_value,
                "unit": "steps",
                "sparkline": get_sparkline_data("Step Count")
            },
            "heart_rate": {
                "value": resting_hr_value,
                "unit": "bpm",
                "sparkline": get_sparkline_data("Resting Heart Rate")
            },
            "hrv": {
                "value": hrv_value,
                "unit": "ms",
                "sparkline": get_sparkline_data("Heart Rate Variability")
            },
            "sleep": {
                "hours": sleep_hours,
                "minutes": sleep_minutes,
                "deep": sleep_deep,
                "rem": sleep_rem,
                "core": sleep_core
            }
        })
    
    except Exception as e:
        print(f"Error in /api/overview: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/detail/{metric}")
async def get_detail(metric: str, range: str = "week"):
    """Get detail data for a specific metric"""
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        # Map time ranges to SQL intervals and aggregation
        range_config = {
            "day": ("1 day", "DATE(timestamp)"),
            "week": ("7 days", "DATE(timestamp)"),
            "month": ("1 month", "DATE(timestamp)"),
            "3month": ("3 months", "DATE(timestamp)"),
            "6month": ("6 months", "DATE_TRUNC('week', DATE(timestamp))"),
            "year": ("1 year", "DATE_TRUNC('week', DATE(timestamp))"),
            "5year": ("5 years", "DATE_TRUNC('month', DATE(timestamp))"),
            "all": ("100 years", "DATE_TRUNC('month', DATE(timestamp))"),
        }
        
        interval, group_by = range_config.get(range, ("7 days", "DATE(timestamp)"))
        
        if metric == "steps":
            # Query daily steps
            result = conn.execute(f"""
                SELECT {group_by} as period, SUM(value) as total_steps
                FROM readings 
                WHERE metric = 'Step Count' 
                AND timestamp > NOW() - INTERVAL '{interval}'
                GROUP BY {group_by}
                ORDER BY period DESC
                LIMIT 150
            """).fetchall()
            
            data = [{"date": str(r[0]), "value": int(r[1])} for r in result]
            
            # Calculate stats
            if result:
                values = [r[1] for r in result]
                stats = {
                    "total": int(sum(values)),
                    "avg": int(sum(values) / len(values)),
                    "max": int(max(values)),
                    "min": int(min(values)),
                }
            else:
                stats = {"total": 0, "avg": 0, "max": 0, "min": 0}
            
            conn.close()
            return JSONResponse({"data": data, "stats": stats, "type": "bar"})
        
        elif metric == "energy":
            # Query daily energy
            result = conn.execute(f"""
                SELECT {group_by} as date, SUM(value) as total_calories
                FROM readings 
                WHERE metric = 'Active Energy' 
                AND timestamp > NOW() - INTERVAL '{interval}'
                GROUP BY {group_by}
                ORDER BY date DESC
                LIMIT 150
            """).fetchall()
            
            data = [{"date": str(r[0]), "value": int(r[1])} for r in result]
            
            if result:
                values = [r[1] for r in result]
                stats = {
                    "total": int(sum(values)),
                    "avg": int(sum(values) / len(values)),
                    "max": int(max(values)),
                }
            else:
                stats = {"total": 0, "avg": 0, "max": 0}
            
            conn.close()
            return JSONResponse({"data": data, "stats": stats, "type": "bar"})
        
        elif metric == "heart":
            # Query resting heart rate
            result = conn.execute(f"""
                SELECT {group_by} as date, AVG(value) as avg_hr, MIN(value) as min_hr, MAX(value) as max_hr
                FROM readings 
                WHERE metric = 'Resting Heart Rate' 
                AND timestamp > NOW() - INTERVAL '{interval}'
                GROUP BY {group_by}
                ORDER BY date DESC
                LIMIT 150
            """).fetchall()
            
            data = [{"date": str(r[0]), "value": round(float(r[1]), 1)} for r in result]
            
            if result:
                avg_vals = [r[1] for r in result]
                stats = {
                    "avg": round(sum(avg_vals) / len(avg_vals), 1),
                    "min": round(min(r[2] for r in result), 1),
                    "max": round(max(r[3] for r in result), 1),
                }
            else:
                stats = {"avg": 0, "min": 0, "max": 0}
            
            conn.close()
            return JSONResponse({"data": data, "stats": stats, "type": "line"})
        
        elif metric == "hrv":
            result = conn.execute(f"""
                SELECT {group_by} as date, AVG(value) as avg_hrv
                FROM readings 
                WHERE metric = 'Heart Rate Variability' 
                AND timestamp > NOW() - INTERVAL '{interval}'
                GROUP BY {group_by}
                ORDER BY date DESC
                LIMIT 150
            """).fetchall()
            
            data = [{"date": str(r[0]), "value": round(float(r[1]), 1)} for r in result]
            
            if result:
                values = [r[1] for r in result]
                stats = {
                    "avg": round(sum(values) / len(values), 1),
                    "min": round(min(values), 1),
                    "max": round(max(values), 1),
                }
            else:
                stats = {"avg": 0, "min": 0, "max": 0}
            
            conn.close()
            return JSONResponse({"data": data, "stats": stats, "type": "line"})
        
        elif metric == "sleep":
            # Query sleep breakdown
            result = conn.execute(f"""
                SELECT 
                    {group_by} as date,
                    MAX(CASE WHEN metric = 'Sleep Analysis [REM]' THEN value ELSE 0 END) as rem,
                    MAX(CASE WHEN metric = 'Sleep Analysis [Deep]' THEN value ELSE 0 END) as deep,
                    MAX(CASE WHEN metric = 'Sleep Analysis [Core]' THEN value ELSE 0 END) as core
                FROM readings 
                WHERE metric LIKE 'Sleep Analysis%'
                AND timestamp > NOW() - INTERVAL '{interval}'
                GROUP BY {group_by}
                ORDER BY date DESC
                LIMIT 150
            """).fetchall()
            
            data = [
                {
                    "date": str(r[0]),
                    "rem": round(float(r[1]), 2),
                    "deep": round(float(r[2]), 2),
                    "core": round(float(r[3]), 2),
                    "total": round(float(r[1]) + float(r[2]) + float(r[3]), 2),
                }
                for r in result
            ]
            
            if result:
                totals = [r[1] + r[2] + r[3] for r in result]
                deep_vals = [r[2] for r in result]
                rem_vals = [r[1] for r in result]
                stats = {
                    "avg_total": round(sum(totals) / len(totals), 2),
                    "avg_deep": round(sum(deep_vals) / len(deep_vals), 2),
                    "avg_rem": round(sum(rem_vals) / len(rem_vals), 2),
                }
            else:
                stats = {"avg_total": 0, "avg_deep": 0, "avg_rem": 0}
            
            conn.close()
            return JSONResponse({"data": data, "stats": stats, "type": "stacked"})
        
        else:
            return JSONResponse({"error": "Unknown metric"}, status_code=400)
    
    except Exception as e:
        print(f"Error in /api/detail/{metric}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
