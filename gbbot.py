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

def save_chat_id(chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        # Chat-ID speichern, wenn sie noch nicht existiert
        cursor.execute('''
            INSERT OR IGNORE INTO event_settings (chat_id, event_date) 
            VALUES (?, 'Noch kein Datum gesetzt')
        ''', (chat_id,))
        
        connection.commit()
        connection.close()
        logger.info(f"Chat-ID {chat_id} erfolgreich gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Chat-ID: {e}")

def set_manual_chat_id(new_chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        # Manuell eingegebene Chat-ID speichern, wenn sie noch nicht existiert
        cursor.execute('''
            INSERT OR IGNORE INTO event_settings (chat_id, event_date) 
            VALUES (?, 'Noch kein Datum gesetzt')
        ''', (new_chat_id,))
        
        connection.commit()
        connection.close()
        logger.info(f"Manuelle Chat-ID {new_chat_id} erfolgreich gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der manuellen Chat-ID: {e}")

# Funktion zur Anzeige und Speicherung der Chat-ID
async def get_and_save_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    save_chat_id(chat_id)  # Speichert die aktuelle Chat-ID in der Datenbank
    
    # Prüft, ob eine manuelle Chat-ID übergeben wurde
    if context.args:
        new_chat_id = " ".join(context.args)
        set_manual_chat_id(new_chat_id)
        await update.message.reply_text(f"Manuelle Chat-ID **{new_chat_id}** wurde gespeichert.", parse_mode="Markdown")
        logger.info(f"Manuelle Chat-ID {new_chat_id} gespeichert.")
    else:
        await update.message.reply_text(f"Die aktuelle Chat-ID ist: **{chat_id}**", parse_mode="Markdown")
        logger.info(f"Chat-ID {chat_id} wurde von {update.effective_user.first_name} abgefragt.")

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

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    app.add_handler(CommandHandler("id", get_and_save_chat_id))
    app.add_handler(CommandHandler("start", start))

    logger.info("Bot wird gestartet...")
    app.run_polling()