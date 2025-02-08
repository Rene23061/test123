import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Phasen der Unterhaltung
SELECT_OPTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, SELECT_PAYMENT, SUMMARY = range(5)

DATE_FILE = "event_date.txt"

def get_current_date():
    try:
        with open(DATE_FILE, "r") as file:
            date = file.read().strip()
            logger.info(f"Datum erfolgreich aus Datei gelesen: {date}")
            return date if date else "Noch kein Datum gesetzt"
    except FileNotFoundError:
        logger.warning("Datei für Veranstaltungsdatum nicht gefunden, Standardwert verwenden.")
        return "Noch kein Datum gesetzt"
    except Exception as e:
        logger.error(f"Fehler beim Lesen des Datums: {e}")
        return "Fehler beim Laden des Datums"

def set_current_date(new_date: str):
    try:
        with open(DATE_FILE, "w") as file:
            file.write(new_date)
            logger.info(f"Neues Datum wurde erfolgreich gespeichert: {new_date}")
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Datums: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = get_current_date()
    
    # Zeitoptionen mit Preisen und Anzahlungen definieren
    options = [
        ["13:00 - 17:00 Uhr\n100€\n25€ Anzahlung"], 
        ["17:00 - 20:00 Uhr\n100€\n25€ Anzahlung"], 
        ["13:00 - 20:00 Uhr\n150€\n50€ Anzahlung"]
    ]
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

async def set_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.args:
            new_date = " ".join(context.args)
            if len(new_date.split(".")) == 3:
                set_current_date(new_date)
                await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{new_date}** geändert.", parse_mode="Markdown")
                logger.info(f"Veranstaltungsdatum durch Benutzer {update.effective_user.first_name} geändert: {new_date}")
                await start(update, context)
            else:
                await update.message.reply_text("Das angegebene Datum hat nicht das richtige Format. Bitte gib es im Format TT.MM.JJJJ ein.")
                logger.warning("Falsches Datumformat erkannt.")
        else:
            await update.message.reply_text("Bitte gib das Datum im Format `/datum TT.MM.JJJJ` ein.")
            logger.warning("Datum wurde nicht übergeben.")
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des Datums: {e}")
        await update.message.reply_text("Es ist ein Fehler beim Setzen des Datums aufgetreten.")

async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_selection = update.message.text
    context.user_data["selected_option"] = user_selection

    logger.info(f"Benutzer hat Option gewählt: {user_selection}")

    await update.message.reply_text(
        "Du kannst jetzt ein Bild hochladen, das für die Buchung relevant ist.\n"
        "Falls du kein Bild hochladen möchtest, schreibe bitte einfach **nein**.",
        parse_mode="Markdown"
    )
    return UPLOAD_IMAGE

# Bild hochladen oder überspringen
async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "nein":
        await update.message.reply_text("Kein Bild hochgeladen. Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION
    
    try:
        photo_file = update.message.photo[-1].file_id  # Letztes (höchste Auflösung)
        context.user_data["photo"] = photo_file  # Speichere das Bild
        logger.info("Bild erfolgreich empfangen und gespeichert.")

        await update.message.reply_text("Bild erhalten! Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des hochgeladenen Bildes: {e}")
        await update.message.reply_text("Es gab ein Problem beim Hochladen des Bildes. Bitte versuche es erneut oder schreibe **nein**, um fortzufahren.")
        return UPLOAD_IMAGE

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    logger.info(f"Beschreibung erhalten: {description}")

    await update.message.reply_text(
        "Wie möchtest du gerne abzahlen?",
        parse_mode="Markdown"
    )
    return SELECT_PAYMENT

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method

    logger.info(f"Zahlungsmethode gewählt: {payment_method}")

    return SELECT_PAYMENT

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_date = get_current_date()
    selected_option = context.user_data["selected_option"]
    description = context.user_data["description"]
    payment_method = context.user_data["payment_method"]
    
    price = selected_option.split("\n")[1]
    deposit = selected_option.split("\n")[2]

    summary_text = (
        f"Zusammenfassung deiner Buchung:\n\n"
        f"Eventdatum: **{selected_date}**\n"
        f"Zeitoption: **{selected_option.split('\\n')[0]}**\n"
        f"Beschreibung: {description}\n"
        f"Zahlungsmethode: {payment_method}\n\n"
        f"Gesamtpreis: {price}, davon Anzahlung: {deposit}\n"
        "Bitte leiste die Anzahlung innerhalb der nächsten 48 Stunden, um deine Teilnahme zu garantieren."
    )

    await update.message.reply_text(summary_text, parse_mode="Markdown")
    return ConversationHandler.END

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
            UPLOAD_IMAGE: [MessageHandler(filters.TEXT | filters.PHOTO, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)],
            SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("datum", set_event_date))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()