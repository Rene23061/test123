import sqlite3

# Datenbankverbindung und Tabelleninitialisierung
def init_db():
    conn = sqlite3.connect('whitelist.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS whitelist (link TEXT PRIMARY KEY)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()
