import json
import time
from typing import Dict, Any

from app.data.db import Database


class CorrectionRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add_correction(self, card: Dict[str, Any]) -> int:
        now = int(time.time())
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO correction_cards (
              sentence_text, source_url, structure_tags, hints, rule_ids,
              user_paraphrase, error_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card["sentence_text"],
                card.get("source_url", ""),
                json.dumps(card.get("structure_tags", {})),
                json.dumps(card.get("hints", [])),
                json.dumps(card.get("rule_ids", [])),
                card.get("user_paraphrase", ""),
                card.get("error_type", "structure"),
                now,
            ),
        )
        self._db.connection.commit()
        return int(cursor.lastrowid)
