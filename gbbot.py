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

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method

    logger.info(f"Zahlungsmethode gewählt: {payment_method}")

    await update.message.reply_text(
        f"Wie möchtest du gerne abzahlen? Gewählte Methode: {payment_method}",
        parse_mode="Markdown"
    )

    return SELECT_PAYMENT

async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_selection = update.message.text
    context.user_data["selected_option"] = user_selection  # Speichere die Auswahl

    logger.info(f"Benutzer hat Option gewählt: {user_selection}")

    await update.message.reply_text(
        "Du kannst jetzt ein Bild hochladen, das für die Buchung relevant ist.\n"
        "Falls du kein Bild hochladen möchtest, schreibe bitte einfach **nein**.",
        parse_mode="Markdown"
    )
    return UPLOAD_IMAGE

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    logger.info(f"Beschreibung erhalten: {description}")

    await update.message.reply_text(
        "Bitte wähle eine Zahlungsmethode aus:",
        parse_mode="Markdown"
    )
    return SELECT_PAYMENT

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_date = get_current_date()
    selected_option = context.user_data["selected_option"]
    description = context.user_data["description"]
    payment_method = context.user_data["payment_method"]

    # Preis und Anzahlung extrahieren
    price = selected_option.split("\n")[1]
    deposit = selected_option.split("\n")[2]

    summary = (
        f"Zusammenfassung deiner Buchung:\n\n"
        f"Eventdatum: **{selected_date}**\n"
        f"Zeitoption: **{selected_option.split('\\n')[0]}**\n"
        f"Beschreibung: {description}\n"
        f"Zahlungsmethode: {payment_method}\n\n"
        f"Gesamtpreis: {price}, davon Anzahlung: {deposit}\n"
        "Bitte leiste die Anzahlung innerhalb der nächsten 48 Stunden, um deine Teilnahme zu garantieren."
    )

    await update.message.reply_text(summary, parse_mode="Markdown")
    return SUMMARY

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