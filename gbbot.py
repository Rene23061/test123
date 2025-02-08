import logging
import sqlite3
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging einrichten
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"

# Gruppen-ID speichern
def save_group_link(user_chat_id: str, group_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO group_links (user_chat_id, group_chat_id)
            VALUES (?, ?)
        ''', (user_chat_id, group_id))
        connection.commit()
        connection.close()
        logger.info(f"Verknüpfung zwischen Benutzer {user_chat_id} und Gruppe {group_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Gruppenverknüpfung: {e}")

# /start im Gruppenchat – Verknüpft und schickt private Nachricht
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        group_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        # Gruppen-ID mit Benutzer verknüpfen
        save_group_link(user_id, group_id)
        
        # Private Nachricht mit Link senden
        bot_username = (await context.bot.get_me()).username
        await update.message.reply_text(
            f"Hallo {update.effective_user.first_name}, ich habe diese Gruppe gespeichert.\n"
            f"Bitte starte den privaten Chat hier: [Privater Chat](https://t.me/{bot_username}?start=private)",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Dieser Befehl kann nur im Gruppenchat verwendet werden.")

# /start im privaten Chat – greift auf die verknüpfte Gruppe zu
async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    group_id = get_linked_group_id(user_id)

    if group_id:
        await update.message.reply_text(f"Willkommen im privaten Chat!\nDie verknüpfte Gruppe hat die ID: {group_id}")
    else:
        await update.message.reply_text("Es ist keine Gruppe verknüpft. Bitte starte den Bot zuerst im Gruppenchat.")

# Verknüpfte Gruppen-ID abrufen
def get_linked_group_id(user_chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT group_chat_id FROM group_links WHERE user_chat_id = ?", (user_chat_id,))
        result = cursor.fetchone()
        connection.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der verknüpften Gruppen-ID: {e}")
        return None

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("DEIN_BOT_TOKEN").build()

    # Handler hinzufügen
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start", start_private, filters=~Chat.GROUPS))

    logger.info("Bot wird gestartet...")
    app.run_polling()