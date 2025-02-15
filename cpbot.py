import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
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

# --- Prüfen, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Nachrichtenkontrolle: Links erkennen und löschen ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    text = message.text or ""

    # Falls der User gerade einen Link hinzufügt, ignorieren wir die Prüfung
    if context.user_data.get("awaiting_link") == chat_id:
        return

    username = f"[@{user.username}](tg://user?id={user.id})" if user.username else f"[{user.full_name}](tg://user?id={user.id})"

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        # Prüfen, ob der Link erlaubt ist
        if not is_whitelisted(chat_id, link):
            try:
                # Nachricht löschen
                await context.bot.delete_message(chat_id, message.message_id)

                # Benutzer benachrichtigen
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {username}, dein Gruppenlink wurde automatisch gelöscht.\n"
                         "Bitte frage einen Admin, falls du Links posten möchtest.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen der Nachricht: {e}")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Nachrichten-Handler mit hoher Priorität registrieren
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht), group=-1)

    print("🚀 Bot läuft und überwacht Gruppenlinks...")
    application.run_polling()

if __name__ == "__main__":
    main()