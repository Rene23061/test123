import logging
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Hilfsfunktion: MarkdownV2-Sonderzeichen escapen
def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

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
    options = [
        ["13:00 - 17:00 Uhr\n100€\n25€ Anzahlung"], 
        ["17:00 - 20:00 Uhr\n100€\n25€ Anzahlung"], 
        ["13:00 - 20:00 Uhr\n150€\n50€ Anzahlung"]
    ]
    reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)
    await update.message.reply_text(
        escape_markdown_v2(
            f"Willkommen zur Veranstaltungsbuchung!\n"
            f"Du möchtest an der Veranstaltung am **{current_date}** teilnehmen.\n"
            "Bitte wähle einen Zeitraum aus:"
        ),
        reply_markup=reply_markup,
        parse_mode="MarkdownV2"
    )
    return SELECT_OPTION

# Option auswählen
async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_selection = update.message.text
    context.user_data["selected_option"] = user_selection
    logger.info(f"Benutzer hat Option gewählt: {user_selection}")
    await update.message.reply_text(
        escape_markdown_v2("Du kannst jetzt ein Bild hochladen oder schreibe **nein**, um fortzufahren."),
        parse_mode="MarkdownV2"
    )
    return UPLOAD_IMAGE

# Bild hochladen oder überspringen
async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Prüfen, ob die Nachricht Text enthält und ob es "nein" ist
    if update.message.text and update.message.text.lower() == "nein":
        await update.message.reply_text("Kein Bild hochgeladen. Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION

    # Prüfen, ob ein Bild hochgeladen wurde
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"downloads/{photo_file.file_id}.jpg"
            await photo_file.download_to_drive(file_path)
            context.user_data["photo_path"] = file_path
            logger.info(f"Bild erfolgreich heruntergeladen: {file_path}")
            await update.message.reply_text("Bild erhalten! Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
            return ENTER_DESCRIPTION
        except Exception as e:
            logger.error(f"Fehler beim Hochladen des Bildes: {e}")
            await update.message.reply_text("Es gab ein Problem beim Hochladen des Bildes. Bitte versuche es erneut oder schreibe **nein**, um fortzufahren.")
            return UPLOAD_IMAGE

    # Wenn weder Text noch Bild vorhanden ist
    await update.message.reply_text("Bitte lade ein gültiges Bild hoch oder schreibe **nein**, um fortzufahren.")
    return UPLOAD_IMAGE

# Beschreibung eingeben
async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description
    logger.info(f"Beschreibung erhalten: {description}")

    payment_options = [["Revolut", "PayPal"], ["Amazon Gutschein"]]
    reply_markup = ReplyKeyboardMarkup(payment_options, one_time_keyboard=True)
    await update.message.reply_text("Bitte wähle eine Zahlungsmethode aus:", reply_markup=reply_markup)
    return SELECT_PAYMENT

# Zahlungsmethode auswählen
async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method
    logger.info(f"Zahlungsmethode gewählt: {payment_method}")

    selected_date = get_current_date()
    selected_option = context.user_data["selected_option"]
    option_lines = selected_option.split("\n")
    selected_time, selected_cost, selected_deposit = option_lines[0], option_lines[1], option_lines[2]

    summary = escape_markdown_v2(
        f"Du möchtest am **{selected_date}** zur Zeit **{selected_time}** teilnehmen.\n\n"
        f"Deine Beschreibung:\n{context.user_data['description']}\n\n"
        f"Zahlungsmethode: {payment_method}\n\n"
        f"**Kostenübersicht:**\n"
        f"Gesamtkosten: {selected_cost}\n"
        f"Anzahlung: {selected_deposit}\n\n"
        "Ohne Anzahlung innerhalb der nächsten 48 Stunden ist keine Teilnahme garantiert."
    )

    await update.message.reply_text(summary, parse_mode="MarkdownV2")

    if payment_method == "PayPal":
        await update.message.reply_text("Bitte überweise an **paypal@example.com**.")
    elif payment_method == "Revolut":
        await update.message.reply_text("Bitte überweise an IBAN **DE123456789**.")
    elif payment_method == "Amazon Gutschein":
        await update.message.reply_text("Sende den Gutschein-Code hier im Chat oder kontaktiere uns.")

    return SUMMARY

# Fallback-Nachricht
async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Entschuldigung, ich habe das nicht verstanden. Bitte verwende eine der Optionen oder /cancel.")

# Beenden des Gesprächs
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Gespräch abgebrochen von Benutzer {update.effective_user.first_name}.")
    await update.message.reply_text("Buchung abgebrochen. Du kannst jederzeit /start eingeben.")
    return ConversationHandler.END

# Datum setzen
async def set_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Bitte gib ein gültiges Datum im Format 'YYYY-MM-DD' an.")
        return

    new_date = context.args[0]
    set_current_date(new_date)
    await update.message.reply_text(
        escape_markdown_v2(f"Das neue Veranstaltungsdatum wurde auf **{new_date}** gesetzt."),
        parse_mode="MarkdownV2"
    )

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
            SUMMARY: [MessageHandler(filters.ALL, fallback_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("datum", set_event_date))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()