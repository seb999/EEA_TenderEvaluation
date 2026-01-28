"""
Migration script to add applicant_id column to PDFOCRCache table
Run this once to update existing database
"""
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "data" / "tender_evaluation.db"

def migrate():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(pdfoorcrcache)")
        columns = [row[1] for row in cursor.fetchall()]

        if "applicant_id" in columns:
            print("✓ Column 'applicant_id' already exists in pdfoorcrcache table")
            return

        # Add the column
        print("Adding 'applicant_id' column to pdfoorcrcache table...")
        cursor.execute("""
            ALTER TABLE pdfoorcrcache
            ADD COLUMN applicant_id INTEGER REFERENCES applicant(id)
        """)

        # Create index
        print("Creating index on applicant_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pdfoorcrcache_applicant_id
            ON pdfoorcrcache (applicant_id)
        """)

        conn.commit()
        print("✓ Migration completed successfully!")

    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if not DATABASE_PATH.exists():
        print(f"✗ Database not found at {DATABASE_PATH}")
        print("Start your application first to create the database.")
    else:
        migrate()
