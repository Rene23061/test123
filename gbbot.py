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
SELECT_OPTION, CONFIRM_SELECTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, SELECT_PAYMENT, CONFIRM_REBOOKING, FINALIZE_BOOKING = range(7)

DATE_FILE = "event_date.txt"
BOOKINGS_WITH_PHOTOS_FILE = "bookings_with_photos.txt"
ADMIN_ID_FILE = "admin_id.txt"

def get_current_date():
    try:
        with open(DATE_FILE, "r") as file:
            date = file.read().strip()
            return date if date else "Noch kein Datum gesetzt"
    except FileNotFoundError:
        return "Noch kein Datum gesetzt"

def get_admin_id():
    if os.path.exists(ADMIN_ID_FILE):
        with open(ADMIN_ID_FILE, "r") as file:
            return file.read().strip()
    return None

def save_admin_id(admin_id: str):
    with open(ADMIN_ID_FILE, "w") as file:
        file.write(admin_id)

def has_existing_booking(user_id: int):
    if os.path.exists(BOOKINGS_WITH_PHOTOS_FILE):
        with open(BOOKINGS_WITH_PHOTOS_FILE, "r") as file:
            for line in file:
                parts = line.strip().split(": ", maxsplit=2)
                if len(parts) >= 3:
                    stored_user_id, stored_date, _ = parts[:3]
                    if str(user_id) == stored_user_id.strip():
                        return stored_date.strip()
    return None

def save_booking_with_photos(user_id: int, date: str, photos: list, payment_method: str):
    try:
        with open(BOOKINGS_WITH_PHOTOS_FILE, "a") as file:
            photo_ids = ",".join(photos)
            file.write(f"{user_id}: {date}: {photo_ids}: {payment_method}\n")
        logger.info(f"Buchung mit Fotos und Zahlungsmethode für Benutzer {user_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Buchung: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing_booking_date = has_existing_booking(user_id)

    if existing_booking_date:
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

    option_lines = user_selection.split("\n")
    selected_deposit = "50€" if "150€" in option_lines[1] else "25€"

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
        return await start(update, context)
    elif user_choice == "Weiter (verstanden)":
        await update.message.reply_text(
            escape_markdown_v2(
                "Du kannst jetzt ein Bild hochladen, das für die Buchung relevant ist.\n"
                "Falls du kein Bild hast, schreibe bitte **nein**."
            ),
            parse_mode="MarkdownV2"
        )
        return UPLOAD_IMAGE

async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.lower() == "nein":
        await update.message.reply_text("Kein Bild hochgeladen. Bitte gib jetzt eine kurze Beschreibung ein.")
        return ENTER_DESCRIPTION

    try:
        context.user_data.setdefault("photos", [])

        # Speichere nur die höchste Auflösung jedes Bildes
        if update.message.photo:
            highest_res_photo = update.message.photo[-1].file_id
            context.user_data["photos"].append(highest_res_photo)

            logger.info(f"Höchste Auflösung des Bildes erfolgreich gespeichert. Aktuell gespeicherte Bilder: {len(context.user_data['photos'])}")
            await update.message.reply_text("Bild gespeichert! Du kannst weitere Bilder hochladen oder **nein** schreiben, um fortzufahren.")
        return UPLOAD_IMAGE

    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des Bild-Uploads: {e}")
        await update.message.reply_text("Es gab ein Problem beim Hochladen der Bilder. Bitte versuche es erneut.")