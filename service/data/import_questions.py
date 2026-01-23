import argparse
import json
import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from models import Question

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_DB_URL = f"sqlite:///{DATA_DIR / 'tender_evaluation.db'}"


def _get_db_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DB_URL


def _ensure_tables(engine):
    SQLModel.metadata.create_all(engine)


def _ensure_blank(session: Session):
    existing = session.exec(select(Question).limit(1)).first()
    if existing:
        raise RuntimeError("Question table is not empty. Use a blank database.")


def _load_payload(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Seed file must contain a JSON array of questions")
    return payload


def _to_prompt_json(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def import_questions(seed_path: Path, engine):
    with Session(engine) as session:
        _ensure_blank(session)

        payload = _load_payload(seed_path)
        created = 0
        for entry in payload:
            q_id = str(entry.get("q_id", "")).strip()
            if not q_id:
                continue

            session.add(
                Question(
                    q_id=q_id,
                    prompt_json=_to_prompt_json(entry.get("prompt_json", {})),
                    is_active=bool(entry.get("is_active", True)),
                    search_label=entry.get("search_label", "Criterion"),
                    auto_increment=bool(entry.get("auto_increment", True)),
                )
            )
            created += 1

        session.commit()

    print(f"Imported {created} questions into blank table.")


def main():
    parser = argparse.ArgumentParser(description="Import questions into a blank database.")
    parser.add_argument(
        "seed_path",
        help="Path to JSON file with a list of questions.",
    )
    args = parser.parse_args()

    seed_path = Path(args.seed_path)
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    engine = create_engine(_get_db_url(), echo=False)
    _ensure_tables(engine)
    import_questions(seed_path, engine)


if __name__ == "__main__":
    main()
