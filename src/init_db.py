#!/usr/bin/env python3
"""
Initialize the health database with schema.

Creates three tables:
- readings: Main fact table for all health metrics
- metrics: Metadata catalog for known metrics
- imports: Log of import operations

Usage:
    python src/init_db.py
"""

import duckdb
import sys
from pathlib import Path
from config import get_db_path

# Database location
DB_PATH = get_db_path()

def init_database():
    """Create database and tables if they don't exist."""
    
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database (creates file if doesn't exist)
    conn = duckdb.connect(str(DB_PATH))
    
    try:
        # Create readings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                timestamp TIMESTAMP NOT NULL,
                metric VARCHAR NOT NULL,
                value DOUBLE NOT NULL,
                unit VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                PRIMARY KEY (timestamp, metric, source)
            )
        """)
        
        # Create indexes for common query patterns
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
            ON readings(timestamp)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_metric 
            ON readings(metric)
        """)
        
        # Create metrics metadata table
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics START 1
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                metric_id INTEGER PRIMARY KEY DEFAULT nextval('seq_metrics'),
                name VARCHAR UNIQUE NOT NULL,
                display_name VARCHAR,
                category VARCHAR,
                unit VARCHAR,
                description VARCHAR
            )
        """)
        
        # Create imports log table
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_imports START 1
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                import_id INTEGER PRIMARY KEY DEFAULT nextval('seq_imports'),
                filename VARCHAR UNIQUE NOT NULL,
                imported_at TIMESTAMP NOT NULL,
                rows_added INTEGER NOT NULL,
                source VARCHAR NOT NULL
            )
        """)
        
        # Verify tables exist
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        table_names = [t[0] for t in tables]
        expected = ['readings', 'metrics', 'imports']
        
        print(f"✅ Database initialized: {DB_PATH}")
        print(f"✅ Created tables: {', '.join(sorted(table_names))}")
        
        # Verify expected tables exist
        missing = set(expected) - set(table_names)
        if missing:
            print(f"⚠️  Warning: Expected tables not found: {', '.join(missing)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
