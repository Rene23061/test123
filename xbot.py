import sqlite3
import asyncio
import nest_asyncio
from telegram.ext import Application

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# ✅ Datenbankverbindung testen
def connect_db():
    try:
        conn = sqlite3.connect('shop_database.db')  # Falls die DB nicht existiert, wird sie erstellt
        cursor = conn.cursor()
        
        # Teste die Verbindung mit einer einfachen Abfrage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📡 Datenbank erfolgreich verbunden! Tabellen gefunden: {tables}")
        conn.close()
    except Exception as e:
        print(f"⚠ Fehler bei der Datenbankverbindung: {e}")

# ✅ Hauptfunktion für den Bot-Start
async def main():
    app = Application.builder().token(TOKEN).build()
    
    print("✅ Bot erfolgreich gestartet!")
    connect_db()  # Teste die Datenbankverbindung
    
    await app.run_polling()

# ✅ Bot starten (Fix für tmux + venv)
if __name__ == '__main__':
    nest_asyncio.apply()  # Verhindert Event-Loop-Probleme in tmux
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())