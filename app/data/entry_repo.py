import sqlite3
import time
from typing import List, Dict, Any

from app.data.db import Database


class EntryRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add_entry(self, entry: Dict[str, Any]) -> tuple[int, bool]:
        now = int(time.time())
        cursor = self._db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO entries (
                  entry_type, text, language, translation, phonetic_us, phonetic_uk,
                  definition, part_of_speech, ipa, word_roots, tense_form,
                  common_meanings, tags, related_entry_ids, grammar_notes,
                  structure_breakdown, key_terms, audio_us_url, audio_uk_url,
                  source_app, raw_llm,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["entry_type"],
                    entry["text"],
                    entry.get("language", "en"),
                    entry.get("translation", ""),
                    entry.get("phonetic_us", ""),
                    entry.get("phonetic_uk", ""),
                    entry.get("definition", ""),
                    entry.get("part_of_speech", ""),
                    entry.get("ipa", ""),
                    entry.get("word_roots", ""),
                    entry.get("tense_form", ""),
                    entry.get("common_meanings", ""),
                    entry.get("tags", ""),
                    entry.get("related_entry_ids", ""),
                    entry.get("grammar_notes", ""),
                    entry.get("structure_breakdown", ""),
                    entry.get("key_terms", ""),
                    entry.get("audio_us_url", ""),
                    entry.get("audio_uk_url", ""),
                    entry.get("source_app", ""),
                    entry.get("raw_llm", ""),
                    now,
                    now,
                ),
            )
            self._db.connection.commit()
            return int(cursor.lastrowid), True
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM entries WHERE text = ?", (entry["text"],))
            row = cursor.fetchone()
            return (int(row["id"]) if row else 0), False

    def list_entries(self) -> List[Dict[str, Any]]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT id, entry_type, text, translation, phonetic_us, phonetic_uk, definition,
                   part_of_speech, ipa, word_roots, tense_form, common_meanings, tags,
                   related_entry_ids, grammar_notes, structure_breakdown, key_terms,
                   created_at
            FROM entries
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_word_entries(self) -> List[Dict[str, Any]]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT id, text, translation, tags
            FROM entries
            WHERE entry_type = 'word'
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_tags(self, entry_id: int, tags: str) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            UPDATE entries
            SET tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (tags, int(time.time()), entry_id),
        )
        self._db.connection.commit()

    def update_related(self, entry_id: int, related_entry_ids: str) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            UPDATE entries
            SET related_entry_ids = ?, updated_at = ?
            WHERE id = ?
            """,
            (related_entry_ids, int(time.time()), entry_id),
        )
        self._db.connection.commit()

    def search_words(self, query: str, exclude_ids: list[int]) -> List[Dict[str, Any]]:
        cursor = self._db.connection.cursor()
        params = ["%{}%".format(query)]
        sql = """
            SELECT id, text
            FROM entries
            WHERE entry_type = 'word' AND text LIKE ?
        """
        if exclude_ids:
            placeholders = ",".join("?" for _ in exclude_ids)
            sql += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)
        sql += " ORDER BY created_at DESC LIMIT 20"
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_entry_texts(self, ids: list[int]) -> Dict[int, str]:
        if not ids:
            return {}
        cursor = self._db.connection.cursor()
        placeholders = ",".join("?" for _ in ids)
        cursor.execute(
            f"SELECT id, text FROM entries WHERE id IN ({placeholders})",
            ids,
        )
        return {int(row["id"]): row["text"] for row in cursor.fetchall()}
