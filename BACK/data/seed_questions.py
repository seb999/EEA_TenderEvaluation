import argparse
import json
import os
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from models import Question

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_DB_URL = f"sqlite:///{DATA_DIR / 'tender_evaluation.db'}"
DEFAULT_SEED_PATH = DATA_DIR / "questions_seed.json"


def _get_db_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DB_URL


def _ensure_tables(engine):
    SQLModel.metadata.create_all(engine)


def _normalize_prompt_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    return value


def export_questions(output_path: Path, engine):
    with Session(engine) as session:
        questions = session.exec(select(Question).order_by(Question.q_id)).all()
        payload = []
        for q in questions:
            payload.append(
                {
                    "q_id": q.q_id,
                    "prompt_json": _normalize_prompt_json(q.prompt_json),
                    "is_active": q.is_active,
                    "search_label": q.search_label,
                    "auto_increment": q.auto_increment,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Exported {len(payload)} questions to {output_path}")


def import_questions(input_path: Path, engine):
    if not input_path.exists():
        raise FileNotFoundError(f"Seed file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Seed file must contain a JSON array of questions")

    with Session(engine) as session:
        created = 0
        updated = 0
        for entry in payload:
            q_id = str(entry.get("q_id", "")).strip()
            if not q_id:
                continue

            prompt_json = entry.get("prompt_json", {})
            if not isinstance(prompt_json, str):
                prompt_json = json.dumps(prompt_json, ensure_ascii=True)

            existing = session.exec(select(Question).where(Question.q_id == q_id)).first()
            if existing:
                existing.prompt_json = prompt_json
                existing.is_active = bool(entry.get("is_active", True))
                existing.search_label = entry.get("search_label", "Criterion")
                existing.auto_increment = bool(entry.get("auto_increment", True))
                session.add(existing)
                updated += 1
            else:
                session.add(
                    Question(
                        q_id=q_id,
                        prompt_json=prompt_json,
                        is_active=bool(entry.get("is_active", True)),
                        search_label=entry.get("search_label", "Criterion"),
                        auto_increment=bool(entry.get("auto_increment", True)),
                    )
                )
                created += 1

        session.commit()

    print(f"Imported questions. Created: {created}, Updated: {updated}")


def main():
    parser = argparse.ArgumentParser(description="Export or import Question records.")
    parser.add_argument(
        "--export",
        dest="export_path",
        help="Export questions to JSON file.",
    )
    parser.add_argument(
        "--import",
        dest="import_path",
        help="Import questions from JSON file.",
    )
    args = parser.parse_args()

    engine = create_engine(_get_db_url(), echo=False)
    _ensure_tables(engine)

    if args.export_path:
        export_questions(Path(args.export_path), engine)
        return

    import_path = Path(args.import_path) if args.import_path else DEFAULT_SEED_PATH
    import_questions(import_path, engine)


if __name__ == "__main__":
    main()
