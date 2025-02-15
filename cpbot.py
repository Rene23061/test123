import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging für Debugging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  # Ändere auf INFO, wenn weniger Logs gewünscht
)

# --- Verbesserter Regex für Telegram-Links ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/[a-zA-Z0-9_/]+")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    result = cursor.fetchone()
    logging.debug(f"📋 Whitelist-Check für {link}: {'✅ Erlaubt' if result else '❌ Nicht erlaubt'}")
    return result is not None

# --- Nachrichtenkontrolle & Link-Löschung ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not message or not message.text:
        return

    user = message.from_user
    text = message.text.strip()
    logging.info(f"📩 Nachricht von {user.full_name} empfangen: {text}")

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.debug(f"🔍 Erkannter Telegram-Link: {link}")

        if not is_whitelisted(chat_id, link):
            try:
                logging.warning(f"🚨 Unerlaubter Link erkannt! Lösche Nachricht von {user.full_name}: {link}")
                await message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {user.full_name}, dein Link wurde gelöscht!\n❌ Nicht erlaubter Link: {link}",
                    reply_to_message_id=message.message_id
                )
            except Exception as e:
                logging.error(f"⚠️ Fehler beim Löschen der Nachricht: {e}")
            return

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Nachrichtenkontrolle mit Debug-Logs
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Anti-Gruppenlink-Bot gestartet... (Debug-Modus aktiv!)")
    application.run_polling()

if __name__ == "__main__":
    main()