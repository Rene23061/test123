import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank herstellen
def connect_db():
    try:
        conn = sqlite3.connect('shop_database.db')  # Falls die DB nicht existiert, wird sie erstellt
        cursor = conn.cursor()

        # Teste die Verbindung mit einer einfachen Abfrage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"📡 Datenbank erfolgreich verbunden! Tabellen gefunden: {tables}")  # ✅ Fehler behoben
        conn.close()
    except Exception as e:
        print(f"⚠ Fehler bei der Datenbankverbindung: {e}")

# Start-Befehl für den Bot
def start(update: Update, context):
    update.message.reply_text("✅ Bot ist erfolgreich gestartet und die Datenbank ist verbunden!")

# Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    app = Application.builder().token(TOKEN).build()

    # Datenbankverbindung testen
    connect_db()

    # Start-Befehl registrieren
    app.add_handler(CommandHandler("start", start))

    # Bot starten
    app.run_polling()

if __name__ == '__main__':
    main()