import sqlite3

DATABASE_FILE = "event_data.db"

def init_db():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    
    # Tabelle für Event-Einstellungen pro Chat (z.B. Datum, Optionen)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_settings (
            chat_id TEXT PRIMARY KEY,
            event_date TEXT NOT NULL,
            option_1 TEXT,
            option_2 TEXT,
            option_3 TEXT
        )
    ''')
    
    # Tabelle für Buchungen (pro Teilnehmer und Zeitfenster)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            name TEXT,
            selected_option TEXT,
            description TEXT,
            photo_file_id TEXT,
            payment_status TEXT DEFAULT 'offen',
            attendance_status TEXT DEFAULT 'offen',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    connection.commit()
    connection.close()
    print("Datenbank und Tabellen wurden erfolgreich eingerichtet.")

if __name__ == "__main__":
    init_db()