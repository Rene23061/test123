import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"

# Phasen der Unterhaltung
SELECT_OPTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, PAYMENT = range(4)

# Funktion zum Speichern des Event-Datums
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

# Funktion zum Abrufen des gespeicherten Event-Datums
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
        logger.error(f"Fehler beim Abrufen des Datums aus der Datenbank: {e}")
        return "Fehler beim Laden des Datums"

# Bot-Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    current_date = get_event_date(chat_id)
    options = [["Option 1", "Option 2"]]
    reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)

    logger.info(f"Startkommando empfangen von {update.effective_user.first_name}.")

    await update.message.reply_text(
        f"Willkommen zur Veranstaltungsbuchung!\n"
        f"Du möchtest an der Veranstaltung am **{current_date}** teilnehmen.\n"
        "Bitte wähle einen Zeitraum aus:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_OPTION

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

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    # /start- und /datum-Befehl registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("datum", set_event_date_command))

    logger.info("Bot wird gestartet...")
    app.run_polling()