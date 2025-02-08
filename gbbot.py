import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Absoluter Pfad zur Datenbank im Root-Verzeichnis
DATABASE_FILE = "/root/event_data.db"

# Phasen der Unterhaltung
SELECT_OPTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, PAYMENT = range(4)

def get_current_date(chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT event_date FROM event_dates WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        connection.close()
        
        if result:
            logger.info(f"Datum erfolgreich aus der Datenbank abgerufen: {result[0]}")
            return result[0]
        else:
            logger.info(f"Kein Datum für Chat {chat_id} gefunden.")
            return "Noch kein Datum gesetzt"
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Datums aus der Datenbank: {e}")
        return "Fehler beim Laden des Datums"

def set_current_date(chat_id: str, new_date: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        
        # Datum setzen oder aktualisieren
        cursor.execute('''
            INSERT INTO event_dates (chat_id, event_date) 
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET event_date=excluded.event_date
        ''', (chat_id, new_date))
        
        connection.commit()
        connection.close()
        logger.info(f"Datum für Chat {chat_id} erfolgreich auf {new_date} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Datums: {e}")

# Bot-Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    current_date = get_current_date(chat_id)
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

# Datum ändern
async def set_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    try:
        if context.args:
            new_date = " ".join(context.args)

            # Einfacher Check für Format TT.MM.JJJJ
            if len(new_date.split(".")) == 3:
                set_current_date(chat_id, new_date)
                await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{new_date}** geändert.", parse_mode="Markdown")
                logger.info(f"Veranstaltungsdatum durch Benutzer {update.effective_user.first_name} geändert: {new_date}")
            else:
                await update.message.reply_text("Das angegebene Datum hat nicht das richtige Format. Bitte gib es im Format TT.MM.JJJJ ein.")
                logger.warning("Falsches Datumformat erkannt.")
        else:
            await update.message.reply_text("Bitte gib das Datum im Format `/datum TT.MM.JJJJ` ein.")
            logger.warning("Datum wurde nicht übergeben. Falsches Format oder fehlende Argumente.")
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des Datums: {e}")
        await update.message.reply_text("Es ist ein Fehler beim Setzen des Datums aufgetreten.")

# Option auswählen
async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_selection = update.message.text
    context.user_data["selected_option"] = user_selection

    logger.info(f"Benutzer hat Option gewählt: {user_selection}")

    await update.message.reply_text(f"Du hast '{user_selection}' gewählt. Bitte lade jetzt ein Bild hoch.")
    return UPLOAD_IMAGE

# Bild hochladen
async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo_file = update.message.photo[-1].file_id
        context.user_data["photo"] = photo_file
        logger.info("Bild erfolgreich empfangen und gespeichert.")

        await update.message.reply_text("Bild erhalten! Bitte gib jetzt eine kurze Beschreibung ein.")
        return ENTER_DESCRIPTION
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des hochgeladenen Bildes: {e}")

# Beschreibung eingeben
async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    logger.info(f"Beschreibung erhalten: {description}")

    await update.message.reply_text(
        "Danke! Hier sind deine Angaben:\n"
        f"Option: {context.user_data['selected_option']}\n"
        f"Beschreibung: {description}\n\n"
        "Zum Abschließen der Buchung überweise bitte die Anzahlung."
    )

    # Zeige ein Beispiel-Bild an (falls nötig)
    photo_id = context.user_data["photo"]
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_id)

    await update.message.reply_text("Hier wäre der Platz für einen Zahlungslink oder Anweisungen.")
    return PAYMENT

# Beenden des Gesprächs
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Gespräch abgebrochen von Benutzer {update.effective_user.first_name}.")
    await update.message.reply_text("Buchung abgebrochen. Du kannst jederzeit /start eingeben, um von vorne zu beginnen.")
    return ConversationHandler.END

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            UPLOAD_IMAGE: [MessageHandler(filters.PHOTO, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("datum", set_event_date))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()