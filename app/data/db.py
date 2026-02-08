import sqlite3


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def initialize(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              entry_type TEXT NOT NULL,
              text TEXT NOT NULL,
              language TEXT NOT NULL DEFAULT 'en',
              translation TEXT DEFAULT '',
              phonetic_us TEXT DEFAULT '',
              phonetic_uk TEXT DEFAULT '',
              definition TEXT DEFAULT '',
              part_of_speech TEXT DEFAULT '',
              ipa TEXT DEFAULT '',
              word_roots TEXT DEFAULT '',
              tense_form TEXT DEFAULT '',
              common_meanings TEXT DEFAULT '',
              tags TEXT DEFAULT '',
              related_entry_ids TEXT DEFAULT '',
              grammar_notes TEXT DEFAULT '',
              structure_breakdown TEXT DEFAULT '',
              key_terms TEXT DEFAULT '',
              audio_us_url TEXT DEFAULT '',
              audio_uk_url TEXT DEFAULT '',
              source_app TEXT DEFAULT '',
              raw_llm TEXT DEFAULT '',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_text ON entries(text);
            CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(entry_type);
            CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);

            CREATE TABLE IF NOT EXISTS reviews (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              entry_id INTEGER NOT NULL,
              stage INTEGER NOT NULL DEFAULT 0,
              next_review_at INTEGER NOT NULL,
              last_review_at INTEGER DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'pending',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_reviews_entry ON reviews(entry_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_next ON reviews(next_review_at);

            CREATE TABLE IF NOT EXISTS review_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              entry_id INTEGER NOT NULL,
              action TEXT NOT NULL,
              reviewed_at INTEGER NOT NULL,
              note TEXT DEFAULT '',
              FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_logs_entry ON review_logs(entry_id);
            CREATE INDEX IF NOT EXISTS idx_logs_time ON review_logs(reviewed_at);

            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            """
        )
        self._ensure_column("entries", "part_of_speech", "TEXT DEFAULT ''")
        self._ensure_column("entries", "ipa", "TEXT DEFAULT ''")
        self._ensure_column("entries", "word_roots", "TEXT DEFAULT ''")
        self._ensure_column("entries", "tense_form", "TEXT DEFAULT ''")
        self._ensure_column("entries", "common_meanings", "TEXT DEFAULT ''")
        self._ensure_column("entries", "tags", "TEXT DEFAULT ''")
        self._ensure_column("entries", "related_entry_ids", "TEXT DEFAULT ''")
        self._ensure_column("entries", "grammar_notes", "TEXT DEFAULT ''")
        self._ensure_column("entries", "structure_breakdown", "TEXT DEFAULT ''")
        self._ensure_column("entries", "key_terms", "TEXT DEFAULT ''")
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in cursor.fetchall()}
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
