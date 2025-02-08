import logging
import sqlite3
from telegram import Update
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

# Bot-Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    current_date = get_event_date(chat_id)
    
    logger.info(f"Startkommando empfangen von {update.effective_user.first_name} in Chat {chat_id}.")

    await update.message.reply_text(
        f"Willkommen zur Veranstaltungsbuchung!\n"
        f"Das aktuelle Event-Datum ist: **{current_date}**\n"
        "Nutze /datum, um das Datum zu ändern.",
        parse_mode="Markdown"
    )

# Datum ändern mit /datum-Befehl
async def set_event_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    try:
        if context.args:
            new_date = " ".join(context.args)
            if len(new_date.split(".")) == 3:  # Einfacher Check für TT.MM.JJJJ-Format
                set_event_date(chat_id, new_date)
                await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{new_date}** geändert.", parse_mode="Markdown")
            else:
                await update.message.reply_text("Das Datum ist ungültig. Bitte gib es im Format TT.MM.JJJJ ein.")
        else:
            await update.message.reply_text("Bitte gib ein Datum im Format `/datum TT.MM.JJJJ` ein.")
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des Datums: {e}")
        await update.message.reply_text("Ein Fehler ist beim Setzen des Datums aufgetreten.")

# /id-Befehl zur Ausgabe der Chat-ID
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(f"Die aktuelle Chat-ID ist: **{chat_id}**", parse_mode="Markdown")
    logger.info(f"Chat-ID {chat_id} wurde von {update.effective_user.first_name} abgefragt.")

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("datum", set_event_date_command))
    app.add_handler(CommandHandler("id", get_chat_id))

    logger.info("Bot wird gestartet...")
    app.run_polling()