"""
Migration script to import existing PDF files into the database
Run this once to import files that were uploaded before database integration
"""
from pathlib import Path
from sqlmodel import Session
from database import engine, create_db_and_tables
from models import Applicant
from datetime import datetime

def migrate_existing_files():
    """Import existing PDF files from uploads directory into database"""

    # Ensure database tables exist
    create_db_and_tables()

    upload_dir = Path("uploads")
    if not upload_dir.exists():
        print("No uploads directory found")
        return

    pdf_files = list(upload_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in uploads directory")
        return

    print(f"Found {len(pdf_files)} PDF files to migrate")

    with Session(engine) as session:
        migrated_count = 0
        skipped_count = 0

        for file_path in pdf_files:
            # Check if file already exists in database
            existing = session.query(Applicant).filter(
                Applicant.filename == file_path.name
            ).first()

            if existing:
                print(f"Skipping {file_path.name} - already in database")
                skipped_count += 1
                continue

            # Extract vendor name from filename (remove .pdf extension)
            vendor_name = file_path.stem

            # Get file stats
            stat = file_path.stat()

            # Create applicant record
            applicant = Applicant(
                vendor_name=vendor_name,
                filename=file_path.name,
                file_path=str(file_path),
                file_size=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime),
                status="uploaded"
            )

            session.add(applicant)
            migrated_count += 1
            print(f"Migrated: {file_path.name}")

        session.commit()
        print(f"\nMigration complete!")
        print(f"Migrated: {migrated_count} files")
        print(f"Skipped: {skipped_count} files")

if __name__ == "__main__":
    migrate_existing_files()
