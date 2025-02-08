import logging
import sqlite3
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"

def set_event_date(chat_id: str, new_date: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        # Neues Datum speichern oder aktualisieren
        cursor.execute('''
            INSERT INTO event_settings (chat_id, event_date) 
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET event_date=excluded.event_date
        ''', (chat_id, new_date))
        
        connection.commit()
        connection.close()
        logger.info(f"Datum für Chat {chat_id} erfolgreich auf {new_date} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Datums: {e}")

def get_event_date(chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT event_date FROM event_settings WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        connection.close()
        
        if result:
            return result[0]
        else:
            return "Noch kein Datum gesetzt"
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Datums: {e}")
        return "Fehler beim Laden des Datums"

def save_group_id(user_chat_id: str, group_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        # Speichern der Gruppen-ID für den Benutzer
        cursor.execute('''
            INSERT OR IGNORE INTO group_links (user_chat_id, group_chat_id)
            VALUES (?, ?)
        ''', (user_chat_id, group_id))
        
        connection.commit()
        connection.close()
        logger.info(f"Verknüpfung zwischen Benutzer {user_chat_id} und Gruppe {group_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Gruppen-ID: {e}")

def get_linked_group_id(user_chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT group_chat_id FROM group_links WHERE user_chat_id = ?", (user_chat_id,))
        result = cursor.fetchone()
        connection.close()

        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der verknüpften Gruppen-ID: {e}")
        return None

# Bot-Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # Prüfen, ob der Bot in einer Gruppe gestartet wurde
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        current_date = get_event_date(chat_id)
        await update.message.reply_text(
            f"Willkommen zur Veranstaltungsbuchung!\n"
            f"Das aktuelle Event-Datum ist: **{current_date}**",
            parse_mode="Markdown"
        )
    else:
        # Im privaten Chat: Prüfen, ob eine Gruppen-ID verknüpft ist
        group_id = get_linked_group_id(chat_id)
        if group_id:
            current_date = get_event_date(group_id)
            await update.message.reply_text(
                f"Willkommen im privaten Chat!\n"
                f"Das Event-Datum der verknüpften Gruppe ist: **{current_date}**",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "Es ist keine Gruppe mit dir verknüpft. Bitte verknüpfe zuerst eine Gruppe mit dem Befehl /id."
            )

# Datum ändern mit /datum-Befehl
async def set_event_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # Prüfen, ob der Befehl in einer Gruppe ausgeführt wurde
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if context.args:
            new_date = " ".join(context.args)
            if len(new_date.split(".")) == 3:  # Einfacher Check für TT.MM.JJJJ-Format
                set_event_date(chat_id, new_date)
                await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{new_date}** geändert.", parse_mode="Markdown")
            else:
                await update.message.reply_text("Das Datum ist ungültig. Bitte gib es im Format TT.MM.JJJJ ein.")
        else:
            await update.message.reply_text("Bitte gib ein Datum im Format `/datum TT.MM.JJJJ` ein.")
    else:
        await update.message.reply_text("Dieser Befehl kann nur in einer Gruppe verwendet werden.")

# /id-Befehl zur Verknüpfung der Gruppe mit einem privaten Benutzer
async def get_and_save_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        group_id = str(update.effective_chat.id)
        await update.message.reply_text(f"Die aktuelle Gruppen-ID ist: **{group_id}**", parse_mode="Markdown")
        logger.info(f"Gruppen-ID {group_id} wurde abgefragt.")
    else:
        if context.args:
            group_id = context.args[0]
            user_chat_id = str(update.effective_chat.id)
            save_group_id(user_chat_id, group_id)
            await update.message.reply_text(f"Die Gruppe mit ID **{group_id}** wurde erfolgreich verknüpft.", parse_mode="Markdown")
        else:
            await update.message.reply_text("Bitte gib eine Gruppen-ID an: `/id [Gruppen-ID]`")

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("datum", set_event_date_command))
    app.add_handler(CommandHandler("id", get_and_save_chat_id))

    logger.info("Bot wird gestartet...")
    app.run_polling()