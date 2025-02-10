import re
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            link TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    print("✅ Datenbank erfolgreich initialisiert.")
    return conn, cursor

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(link, cursor):
    cursor.execute("SELECT link FROM whitelist WHERE link = ?", (link,))
    result = cursor.fetchone()
    return result is not None

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user.username if message.from_user else "Unbekannt"
    text = message.text or ""

    # Konsolenausgabe der empfangenen Nachricht
    print(f"📩 Nachricht empfangen von @{user}: {text}")

    # Nach Telegram-Gruppenlinks suchen
    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)  # Der vollständige erkannte Link
        print(f"🔗 Erkannter Telegram-Link: {link}")

        # Wenn der Link nicht in der Whitelist steht, Nachricht löschen
        if not is_whitelisted(link, cursor):
            print(f"❌ Link nicht erlaubt und wird gelöscht: {link}")
            
            # Freundliche Nachricht an den Benutzer senden
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Hallo @{user}, dein Link wurde automatisch gelöscht. "
                     f"Bitte kontaktiere einen Admin, wenn du Fragen hast.",
                reply_to_message_id=message.message_id
            )
            # Nachricht löschen
            await context.bot.delete_message(chat_id, message.message_id)
            return  # Nach der ersten gefundenen und gelöschten Nachricht abbrechen

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot wird gestartet und überwacht Telegram-Gruppenlinks...")
    application.run_polling()

if __name__ == "__main__":
    main()