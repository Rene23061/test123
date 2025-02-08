
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

# Bot-Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = get_current_date()
    
    # Optionen mit 3 Zeilen pro Button zusammenfassen
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

# Option auswählen
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

# Bild hochladen oder überspringen
async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "nein":
        await update.message.reply_text("Kein Bild hochgeladen. Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION

    # Wenn ein Bild hochgeladen wurde
    if update.message.photo:
        try:
            # Hole die Datei-ID des Bildes mit der höchsten Auflösung
            photo_file = update.message.photo[-1].file_id
            context.user_data["photo"] = photo_file  # Speichere die Bild-ID
            logger.info("Bild erfolgreich empfangen und gespeichert.")

            await update.message.reply_text("Bild erhalten! Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
            return ENTER_DESCRIPTION
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten des hochgeladenen Bildes: {e}")
            await update.message.reply_text("Es gab ein Problem beim Hochladen des Bildes. Bitte versuche es erneut oder schreibe **nein**, um fortzufahren.")
            return UPLOAD_IMAGE
    else:
        # Falls weder Text noch Bild vorhanden sind, Aufforderung zur Wiederholung
        await update.message.reply_text("Bitte lade ein gültiges Bild hoch oder schreibe **nein**, um fortzufahren.")
        return UPLOAD_IMAGE

# Beschreibung eingeben
async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    logger.info(f"Beschreibung erhalten: {description}")

    # Auswahl der Zahlungsmethode
    payment_options = [["Revolut", "PayPal"], ["Amazon Gutschein"]]
    reply_markup = ReplyKeyboardMarkup(payment_options, one_time_keyboard=True)

    await update.message.reply_text(
        "Bitte wähle eine Zahlungsmethode aus:",
        reply_markup=reply_markup
    )
    return SELECT_PAYMENT

# Zahlungsmethode auswählen
async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method

    logger.info(f"Zahlungsmethode gewählt: {payment_method}")

    # Zusammenfassung
    selected_date = get_current_date()
    selected_option = context.user_data["selected_option"]

    # Extrahieren der gewählten Zeit, Kosten und Anzahlung
    option_lines = selected_option.split("\n")
    selected_time = option_lines[0]  # Die Zeitangabe (erste Zeile)
    selected_cost = option_lines[1]  # Die Kosten (zweite Zeile)
    selected_deposit = option_lines[2]  # Die Anzahlung (dritte Zeile)

    summary = (
        f"Du möchtest am **{selected_date}** zur Zeit **{selected_time}** an meinem Event teilnehmen.\n\n"
        f"Deine Beschreibung:\n{context.user_data['description']}\n\n"
        f"Zahlungsmethode: {payment_method}\n\n"
        f"**Kostenübersicht:**\n"
        f"Gesamtkosten: {selected_cost}\n"
        f"Anzahlung: {selected_deposit}\n\n"
        "Ohne Anzahlung innerhalb der nächsten 48 Stunden ist keine Teilnahme garantiert."
    )

    await update.message.reply_text(summary, parse_mode="Markdown")

    # Anweisungen zur Zahlung
    if payment_method == "PayPal":
        await update.message.reply_text("Bitte überweise den Betrag an **paypal@example.com**.")
    elif payment_method == "Revolut":
        await update.message.reply_text("Bitte überweise den Betrag an IBAN **DE123456789**.")
    elif payment_method == "Amazon Gutschein":
        await update.message.reply_text(
            "Bitte sende den Gutschein-Code hier im Chat oder kontaktiere uns direkt."
        )

    return SUMMARY

# Beenden des Gesprächs
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Gespräch abgebrochen von Benutzer {update.effective_user.first_name}.")
    await update.message.reply_text("Buchung abgebrochen. Du kannst jederzeit /start eingeben, um von vorne zu beginnen.")
    return ConversationHandler.END

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    # Gesprächssteuerung
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            UPLOAD_IMAGE: [MessageHandler(filters.TEXT | filters.PHOTO, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)],
            SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Handler für Datum setzen
    app.add_handler(CommandHandler("datum", set_event_date))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()