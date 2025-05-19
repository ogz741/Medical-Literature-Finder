"""
Utility script to clear journal rankings cache in the database.
Run this when you need to force a refresh of journal impact factor data.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add the parent directory to the Python path to allow importing from app
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from app.database_manager import DatabaseManager, DATABASE_FILE

def clear_journal_rankings_cache():
    """Clear all journal rankings from the database cache."""
    print(f"Clearing journal rankings cache from database: {DATABASE_FILE}")
    
    # Check if database exists
    if not DATABASE_FILE.exists():
        print("Database file does not exist. No action needed.")
        return
    
    # Connect directly to the database to clear the cache
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journal_rankings_cache'")
        if not cursor.fetchone():
            print("Journal rankings cache table does not exist. No action needed.")
            conn.close()
            return
        
        # Clear the table
        cursor.execute("DELETE FROM journal_rankings_cache")
        conn.commit()
        
        # Get number of rows affected
        row_count = cursor.rowcount
        print(f"Cleared {row_count} entries from journal rankings cache.")
        
        conn.close()
        print("Cache clearing completed successfully.")
    except sqlite3.Error as e:
        print(f"Error clearing cache: {e}")
        sys.exit(1)

def clear_file_cache():
    """Clear all journal rankings cache files."""
    cache_dir = Path(__file__).resolve().parent / "rankings_cache"
    print(f"Clearing journal rankings cache files from: {cache_dir}")
    
    # Check if directory exists
    if not cache_dir.exists():
        print("Cache directory does not exist. No action needed.")
        return
    
    # Clear all json files in the directory
    try:
        count = 0
        for file_path in cache_dir.glob("*.json"):
            print(f"Removing file: {file_path.name}")
            file_path.unlink()
            count += 1
        
        print(f"Removed {count} cache files.")
    except Exception as e:
        print(f"Error clearing file cache: {e}")
        sys.exit(1)

if __name__ == "__main__":
    clear_journal_rankings_cache()
    clear_file_cache()
    print("\nAll caches cleared. Please restart the application to see the changes.") 