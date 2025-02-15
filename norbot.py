import re
import sqlite3
from telegram import Update, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

# --- Verbindung zur SQLite-Datenbank ---
def init_db():
    conn = sqlite3.connect("topics.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            chat_id INTEGER,
            topic_id INTEGER
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Thema gesperrt ist ---
def is_topic_restricted(chat_id, topic_id):
    cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
    return cursor.fetchone() is not None

# --- Prüfen, ob der Benutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int):
    chat_member = await update.effective_chat.get_member(user_id)
    return isinstance(chat_member, (ChatMemberAdministrator, ChatMemberOwner))

# --- Nachrichten-Handler für gesperrte Themen ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    topic_id = message.message_thread_id  # Thema-ID der Nachricht
    user_id = message.from_user.id

    # Prüfen, ob das Thema gesperrt ist
    if topic_id and is_topic_restricted(chat_id, topic_id):
        if not await is_admin(update, user_id):  # Admins dürfen schreiben
            await message.delete()
            await context.bot.send_message(chat_id, f"🚫 @{message.from_user.username}, du kannst hier nicht schreiben!", reply_to_message_id=message.message_id)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Nachrichten-Handler für gesperrte Themen
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()