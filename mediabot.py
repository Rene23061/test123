import sqlite3
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# 🔹 Test-Bot-Token
TOKEN = "8069716549:AAGfRNlsOIOlsMBZrAcsiB_IjV5yz3XOM8A"

# 🔹 Verbindung zur SQLite-Datenbank herstellen
def init_db():
    conn = sqlite3.connect("mediabot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_topics (
            chat_id INTEGER, 
            topic_id INTEGER, 
            PRIMARY KEY (chat_id, topic_id)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# 🔹 Prüfen, ob ein Thema eingeschränkt ist
def is_topic_restricted(chat_id, topic_id):
    cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
    return cursor.fetchone() is not None

# 🔹 Nachrichten-Handler (löscht Textnachrichten in eingeschränkten Themen)
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.is_topic_message:
        chat_id = update.message.chat_id
        topic_id = update.message.message_thread_id  # Thema-ID

        # Prüfen, ob das Thema eingeschränkt ist
        if is_topic_restricted(chat_id, topic_id):
            # Prüfen, ob die Nachricht nur Text enthält
            if not (update.message.photo or update.message.video or update.message.document):
                await update.message.delete()  # Nachricht löschen
                return

# 🔹 Bot starten
def main():
    application = Application.builder().token(TOKEN).build()

    # Nachrichtenfilter
    application.add_handler(MessageHandler(filters.ALL, filter_messages))

    print("🤖 Medien-Bot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()