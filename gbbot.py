import logging
import re
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# Phasen der Unterhaltung
SELECT_OPTION, CONFIRM_SELECTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, SELECT_PAYMENT, SUMMARY, CONFIRM_REBOOKING = range(7)

DATE_FILE = "event_date.txt"
USER_BOOKINGS_FILE = "user_bookings.txt"

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

def has_existing_booking(user_id: int):
    if os.path.exists(USER_BOOKINGS_FILE):
        with open(USER_BOOKINGS_FILE, "r") as file:
            for line in file:
                stored_user_id, stored_date = line.strip().split(": ")
                if str(user_id) == stored_user_id:
                    return stored_date  # Benutzer hat bereits eine Buchung
    return None  # Keine Buchung gefunden

def save_booking(user_id: int, date: str):
    with open(USER_BOOKINGS_FILE, "a") as file:
        file.write(f"{user_id}: {date}\n")
    logger.info(f"Buchung gespeichert: UserID={user_id}, Datum={date}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing_booking_date = has_existing_booking(user_id)

    if existing_booking_date:
        # Benutzer hat bereits eine Buchung, nach Bestätigung fragen
        reply_markup = ReplyKeyboardMarkup([["Ja, neuen Termin buchen", "Nein, abbrechen"]], one_time_keyboard=True)
        await update.message.reply_text(
            escape_markdown_v2(
                f"Du hast bereits einen Termin am **{existing_booking_date}** gebucht.\n"
                "Möchtest du einen weiteren Termin buchen?"
            ),
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        return CONFIRM_REBOOKING

    # Benutzer hat keine bestehende Buchung
    await proceed_to_booking(update, context)
    return SELECT_OPTION

async def confirm_rebooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text

    if user_choice == "Ja, neuen Termin buchen":
        await update.message.reply_text("Okay, lass uns mit der neuen Buchung starten!")
        return await proceed_to_booking(update, context)
    elif user_choice == "Nein, abbrechen":
        await update.message.reply_text("Buchung abgebrochen. Du kannst jederzeit /start eingeben.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Bitte wähle entweder 'Ja, neuen Termin buchen' oder 'Nein, abbrechen'.")
        return CONFIRM_REBOOKING

async def proceed_to_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = get_current_date()
    options = [
        ["13:00 - 17:00 Uhr\n100€"], 
        ["17:00 - 20:00 Uhr\n100€"], 
        ["13:00 - 20:00 Uhr\n150€"]
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

async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_selection = update.message.text
    context.user_data["selected_option"] = user_selection
    logger.info(f"Benutzer hat Option gewählt: {user_selection}")

    option_lines = user_selection.split("\n")
    if "150€" in option_lines[1]:
        selected_deposit = "50€"
    else:
        selected_deposit = "25€"

    reply_markup = ReplyKeyboardMarkup([["Zurück", "Weiter (verstanden)"]], one_time_keyboard=True)
    await update.message.reply_text(
        escape_markdown_v2(
            f"Aufgrund häufiger kurzfristiger Absagen ist eine Anzahlung in Höhe von **{selected_deposit}** erforderlich.\n"
            "Bitte bestätige, dass du dies verstanden hast."
        ),
        reply_markup=reply_markup,
        parse_mode="MarkdownV2"
    )
    return CONFIRM_SELECTION

async def confirm_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text

    if user_choice == "Zurück":
        return await proceed_to_booking(update, context)
    elif user_choice == "Weiter (verstanden)":
        await update.message.reply_text(
            escape_markdown_v2(
                "Du kannst jetzt ein Bild hochladen, das für die Buchung relevant ist.\n"
                "Falls du kein Bild hochladen möchtest, schreibe bitte einfach **nein**."
            ),
            parse_mode="MarkdownV2"
        )
        return UPLOAD_IMAGE
    else:
        await update.message.reply_text("Bitte wähle entweder 'Zurück' oder 'Weiter (verstanden)'.")
        return CONFIRM_SELECTION

async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.lower() == "nein":
        await update.message.reply_text("Kein Bild hochgeladen. Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION

    if update.message.photo:
        try:
            photo_file_id = update.message.photo[-1].file_id
            context.user_data["photo_id"] = photo_file_id
            logger.info(f"Bild erfolgreich empfangen: {photo_file_id}")

            await update.message.reply_text("Bild erhalten! Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
            return ENTER_DESCRIPTION
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten des hochgeladenen Bildes: {e}")
            await update.message.reply_text("Es gab ein Problem beim Hochladen des Bildes. Bitte versuche es erneut oder schreibe **nein**, um fortzufahren.")
            return UPLOAD_IMAGE

    await update.message.reply_text("Bitte lade ein gültiges Bild hoch oder schreibe **nein**, um fortzufahren.")
    return UPLOAD_IMAGE

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description
    logger.info(f"Beschreibung erhalten: {description}")

    payment_options = [["Revolut", "PayPal"], ["Amazon Gutschein"]]
    reply_markup = ReplyKeyboardMarkup(payment_options, one_time_keyboard=True)
    await update.message.reply_text("Bitte wähle eine Zahlungsmethode aus:", reply_markup=reply_markup)
    return SELECT_PAYMENT

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method
    logger.info(f"Zahlungsmethode gewählt: {payment_method}")

    selected_date = get_current_date()
    save_booking(update.effective_user.id, selected_date)  # Buchung speichern

    summary = escape_markdown_v2(
        f"Du möchtest am **{selected_date}** zur Zeit **{context.user_data['selected_option'].splitlines()[0]}** teilnehmen.\n\n"
        f"Deine Beschreibung:\n{context.user_data['description']}\n\n"
        f"Zahlungsmethode: {payment_method}\n\n"
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

async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Entschuldigung, ich habe das nicht verstanden. Bitte verwende eine der Optionen oder /cancel.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Gespräch abgebrochen von Benutzer {update.effective_user.first_name}.")
    await update.message.reply_text("Buchung abgebrochen. Du kannst jederzeit /start eingeben.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CONFIRM_REBOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_rebooking)],
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            CONFIRM_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_selection)],
            UPLOAD_IMAGE: [MessageHandler(filters.TEXT | filters.PHOTO, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)],
            SUMMARY: [MessageHandler(filters.ALL, fallback_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    logger.info("Bot wird gestartet...")
    app.run_polling()