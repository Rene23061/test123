import logging
import sqlite3
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext

# Dein Bot-Token
BOT_TOKEN = "7720861006:AAGbTV0_haSgPhtNsv2unqy6ZiyI7A_BrBU"

# Logging aktivieren
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Verbindung zur SQLite-Datenbank
def init_db():
    conn = sqlite3.connect("/pfad/zu/deinem/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY,
            allow_sbot INTEGER DEFAULT 0,
            allow_idbot INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# Prüft, ob eine Gruppe erlaubt ist
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_sbot FROM allowed_groups WHERE chat_id = ? AND allow_sbot = 1", (chat_id,))
    return cursor.fetchone() is not None

async def delete_system_messages(update: Update, context: CallbackContext):
    """Löscht neue Systemnachrichten automatisch, falls erlaubt."""
    if update.message:
        chat_id = update.message.chat_id

        # Prüfen, ob die Gruppe erlaubt ist
        if not is_group_allowed(chat_id):
            logging.info(f"⛔ Gruppe {chat_id} ist nicht erlaubt. Ignoriere Nachricht.")
            return

        if update.message.new_chat_members or update.message.left_chat_member or update.message.pinned_message:
            try:
                await update.message.delete()
                logging.info(f"✅ Systemnachricht gelöscht in Chat {chat_id}")
            except BadRequest as e:
                logging.warning(f"⚠️ Nachricht konnte nicht gelöscht werden: {e}")

def main():
    """Startet den Telegram-Bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Überwacht Systemnachrichten und löscht sie, falls die Gruppe erlaubt ist
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_system_messages))

    logging.info("🚀 Bot läuft und löscht neue Systemnachrichten...")
    app.run_polling()

if __name__ == "__main__":
    main()