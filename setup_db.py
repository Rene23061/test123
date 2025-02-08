import sqlite3

DATABASE_FILE = "event_data.db"

def init_db():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    
    # Tabelle für Veranstaltungsdatum (pro Chat)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_dates (
            chat_id TEXT PRIMARY KEY,
            event_date TEXT NOT NULL
        )
    ''')
    
    # Tabelle für Buchungen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            name TEXT NOT NULL,
            option TEXT,
            description TEXT,
            photo_file_id TEXT,
            payment_status TEXT DEFAULT 'offen',  -- Zahlung offen oder bezahlt
            attendance_status TEXT DEFAULT 'offen',  -- Erscheinen offen, anwesend, nicht erschienen
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    connection.commit()
    connection.close()
    print("Datenbank und Tabellen wurden erfolgreich erweitert.")

if __name__ == "__main__":
    init_db()