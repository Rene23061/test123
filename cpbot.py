import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank ---
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

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Sichere Methode zur Ermittlung von chat_id ---
def get_chat_id(update: Update):
    if update.message:
        return update.message.chat_id
    elif update.callback_query:
        return update.callback_query.message.chat_id
    return None

# --- Nachrichtenkontrolle (fix: 100% sicheres Löschen unerlaubter Links) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return  

    message = update.message
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        link_in_whitelist = cursor.fetchone()

        if link_in_whitelist is None:
            try:
                await context.bot.delete_message(chat_id, message.message_id)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 Der Link von {message.from_user.full_name} wurde entfernt.",
                    reply_to_message_id=message.message_id
                )
                print(f"❌ Unerlaubter Link gelöscht: {link}")
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen der Nachricht: {e}")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Fix: Nachrichten-Handler mit `filters.TEXT` & hoher Priorität
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht), group=-1)

    print("🤖 Bot gestartet und überprüft jetzt wirklich alle Nachrichten!")
    application.run_polling()

if __name__ == "__main__":
    main()