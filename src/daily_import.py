#!/usr/bin/env python3
"""
Daily health data import job.

Scans the iCloud folder for Health Auto Export CSV files and imports any
that haven't been processed yet. Safe to run multiple times (idempotent).

Usage:
    python src/daily_import.py
    python src/daily_import.py --dry-run
"""

import duckdb
import argparse
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path to import from same package
sys.path.insert(0, str(Path(__file__).parent))
from import_healthkit import import_csv
from import_medications import import_medications_csv
from import_workouts import import_workouts_csv
from validate import run_validation
from config import get_db_path, get_icloud_folder

# Paths from config
DB_PATH = get_db_path()
ICLOUD_FOLDER = get_icloud_folder()

def get_csv_files(folder_path):
    """
    Find all CSV files in the folder.
    
    Returns:
        list: List of Path objects for CSV files
    """
    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        return []
    
    csv_files = sorted(folder_path.glob("*.csv"))
    return csv_files

def get_imported_files():
    """
    Get list of already-imported filenames from database.
    
    Returns:
        set: Set of imported filenames
    """
    conn = duckdb.connect(str(DB_PATH))
    try:
        result = conn.execute("SELECT filename FROM imports").fetchall()
        return {row[0] for row in result}
    finally:
        conn.close()

def run_daily_import(dry_run=False):
    """
    Scan for new CSV files and import them.
    
    Args:
        dry_run: If True, only report what would be imported
    
    Returns:
        dict: Summary statistics
    """
    print(f"🔍 Scanning: {ICLOUD_FOLDER}")
    
    # Find all CSVs
    csv_files = get_csv_files(ICLOUD_FOLDER)
    
    if not csv_files:
        print("⚠️  No CSV files found")
        return {"total": 0, "new": 0, "skipped": 0, "imported": 0, "errors": 0}
    
    print(f"📂 Found {len(csv_files)} CSV file(s)")
    
    # Get already-imported files
    imported = get_imported_files()
    
    # Identify new files
    new_files = [f for f in csv_files if f.name not in imported]
    
    stats = {
        "total": len(csv_files),
        "new": len(new_files),
        "skipped": len(csv_files) - len(new_files),
        "imported": 0,
        "errors": 0,
        "rows_added": 0
    }
    
    if not new_files:
        print("✨ No new files to import (all up to date)")
        return stats
    
    print(f"\n📥 New files to import: {len(new_files)}")
    for f in new_files:
        print(f"   - {f.name}")
    
    if dry_run:
        print("\n🏃 Dry run mode — no imports performed")
        return stats
    
    # Import new files
    print("\n⚙️  Importing...")
    for csv_file in new_files:
        print(f"\n→ {csv_file.name}")
        
        # Route to appropriate importer based on filename
        if csv_file.name.startswith("Medications-"):
            rows = import_medications_csv(csv_file)
        elif csv_file.name.startswith("Workouts-"):
            rows = import_workouts_csv(csv_file)
        elif csv_file.name.startswith("HealthMetrics-"):
            rows = import_csv(csv_file)
        elif csv_file.name.startswith("HaishanYe_glucose_"):
            # Skip glucose files - handled separately by import_libre.py
            print(f"⏭️  Skipping glucose file (handled by import_libre.py)")
            stats["skipped"] += 1
            continue
        else:
            print(f"⚠️  Unknown file type, attempting HealthKit import...")
            rows = import_csv(csv_file)
        
        if rows < 0:
            stats["errors"] += 1
        else:
            stats["imported"] += 1
            stats["rows_added"] += rows
    
    return stats

def print_summary(stats):
    """Print summary of import run."""
    print("\n" + "="*60)
    print("📊 IMPORT SUMMARY")
    print("="*60)
    print(f"Total CSV files:     {stats['total']}")
    print(f"Already imported:    {stats['skipped']}")
    print(f"New files found:     {stats['new']}")
    print(f"Successfully imported: {stats['imported']}")
    print(f"Errors:              {stats['errors']}")
    if stats['rows_added'] > 0:
        print(f"Total rows added:    {stats['rows_added']}")
    print("="*60)
    
    if stats['imported'] > 0:
        print("✅ Import complete!")
    elif stats['new'] == 0:
        print("✅ All files up to date")
    else:
        print("⚠️  Some imports failed")

def main():
    parser = argparse.ArgumentParser(description="Daily health data import")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be imported without importing")
    args = parser.parse_args()
    
    print("🏥 Health Data Daily Import")
    print(f"⏰ Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run: python src/init_db.py")
        sys.exit(1)
    
    # Run import
    stats = run_daily_import(dry_run=args.dry_run)
    
    # Print summary
    print_summary(stats)
    
    # Run data quality validation
    if not args.dry_run and (stats['imported'] > 0 or stats['total'] > 0):
        print("\n⚙️  Running data quality checks...")
        validation_report = run_validation(verbose=False)
        if validation_report:
            validation_report.print_report(verbose=False)
    
    # Exit with error code if there were errors
    sys.exit(1 if stats['errors'] > 0 else 0)

if __name__ == "__main__":
    main()
