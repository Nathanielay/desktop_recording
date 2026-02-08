import sqlite3
conn = sqlite3.connect("data.sqlite")
cur = conn.cursor()
cur.execute("select id, entry_type, text, translation, raw_llm from entries order by id desc limit 1")
print(cur.fetchone())
