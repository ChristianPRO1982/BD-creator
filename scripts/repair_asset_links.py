from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select  # noqa: E402

from app.db.models import Asset, Comic  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.storage.s3 import storage  # noqa: E402


def repair(comic_id: uuid.UUID | None = None, dry_run: bool = False) -> tuple[int, int]:
    db = SessionLocal()
    removed = 0
    added = 0
    try:
        comics_stmt = select(Comic)
        if comic_id is not None:
            comics_stmt = comics_stmt.where(Comic.id == comic_id)
        comics = db.scalars(comics_stmt).all()

        for comic in comics:
            assets = db.scalars(select(Asset).where(Asset.comic_id == comic.id)).all()
            existing_keys: set[str] = set()

            for asset in assets:
                key = storage.key_from_url(asset.file_path)
                if not key or not storage.object_exists(key):
                    print(f"[remove] missing object -> asset {asset.id} ({asset.name})")
                    if not dry_run:
                        db.delete(asset)
                    removed += 1
                else:
                    existing_keys.add(key)

            prefix = f"comics/{comic.id}/assets/"
            object_keys = storage.list_objects(prefix)

            for key in object_keys:
                if key.endswith("/"):
                    continue
                if key in existing_keys:
                    continue
                expected_url = storage.file_url_for_key(key)
                name = Path(key).name.split("_", 1)[-1] if "_" in Path(key).name else Path(key).name
                print(f"[add] orphan object -> {key} as asset '{name}'")
                if not dry_run:
                    db.add(
                        Asset(
                            comic_id=comic.id,
                            user_id=comic.user_id,
                            name=name,
                            file_path=expected_url,
                        )
                    )
                added += 1

        if not dry_run:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()

    return removed, added


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair asset DB/object storage links.")
    parser.add_argument("--comic-id", type=str, default=None, help="Limit repair to a single comic UUID")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without applying changes")
    args = parser.parse_args()

    comic_id = uuid.UUID(args.comic_id) if args.comic_id else None
    removed, added = repair(comic_id=comic_id, dry_run=args.dry_run)
    print(f"done: removed={removed}, added={added}, dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
