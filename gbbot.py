import logging
import re
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    PicklePersistence,
    filters,
)

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# Phasen der Unterhaltung
SELECT_OPTION, CONFIRM_SELECTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, SELECT_PAYMENT, FINALIZE_BOOKING = range(6)

DATE_FILE = "event_date.txt"
BOOKINGS_WITH_PHOTOS_FILE = "bookings_with_photos.txt"
ADMIN_ID_FILE = "admin_id.txt"

def get_current_date():
    try:
        with open(DATE_FILE, "r") as file:
            return file.read().strip() or "Noch kein Datum gesetzt"
    except FileNotFoundError:
        return "Noch kein Datum gesetzt"

def set_event_date(date: str):
    with open(DATE_FILE, "w") as file:
        file.write(date)

def get_admin_id():
    if os.path.exists(ADMIN_ID_FILE):
        with open(ADMIN_ID_FILE, "r") as file:
            return file.read().strip()
    return None

def save_admin_id(admin_id: str):
    with open(ADMIN_ID_FILE, "w") as file:
        file.write(admin_id)

def get_existing_booking(user_id: int):
    if os.path.exists(BOOKINGS_WITH_PHOTOS_FILE):
        with open(BOOKINGS_WITH_PHOTOS_FILE, "r") as file:
            for line in file:
                parts = line.strip().split(": ", maxsplit=4)
                if len(parts) >= 5 and str(user_id) == parts[0].strip():
                    booking_time = parts[2].strip()
                    booked_event_date = parts[1].strip()
                    return booking_time, booked_event_date
    return None, None

def save_booking_with_photos(user_id: int, date: str, photos: list, payment_method: str, deposit: str):
    try:
        with open(BOOKINGS_WITH_PHOTOS_FILE, "a") as file:
            photo_ids = ",".join(photos)
            booking_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{user_id}: {date}: {booking_time}: {photo_ids}: {payment_method}: {deposit}\n")
        logger.info(f"Buchung für Benutzer {user_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Buchung: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    booking_time, booked_event_date = get_existing_booking(user_id)

    if booking_time and booked_event_date:
        await update.message.reply_text(
            escape_markdown_v2(
                f"Du hast bereits am **{booking_time}** einen Termin für den **{booked_event_date}** gebucht.\n"
                "Falls du einen neuen Termin buchen möchtest, gib /new ein."
            ),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    await proceed_to_booking(update, context)
    return SELECT_OPTION

async def proceed_to_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = get_current_date()
    options = [["13:00 - 17:00 Uhr\n100€"], ["17:00 - 20:00 Uhr\n100€"], ["13:00 - 20:00 Uhr\n150€"]]
    reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)
    await update.message.reply_text(
        escape_markdown_v2(
            f"Willkommen zur Veranstaltungsbuchung!\nDu möchtest an der Veranstaltung am **{current_date}** teilnehmen.\n"
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
    context.user_data["selected_deposit"] = selected_deposit

    reply_markup = ReplyKeyboardMarkup([["Zurück", "Weiter"]], one_time_keyboard=True)
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
    if update.message.text == "Zurück":
        return await proceed_to_booking(update, context)

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

    context.user_data.setdefault("photos", [])
    if update.message.photo:
        context.user_data["photos"].append(update.message.photo[-1].file_id)
        await update.message.reply_text("Bild gespeichert! Du kannst weitere Bilder hochladen oder **nein** schreiben, um fortzufahren.")
    return UPLOAD_IMAGE

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    payment_options = [["Revolut", "PayPal"], ["Amazon Gutschein"]]
    reply_markup = ReplyKeyboardMarkup(payment_options, one_time_keyboard=True)
    await update.message.reply_text("Bitte wähle eine Zahlungsmethode aus:", reply_markup=reply_markup)
    return SELECT_PAYMENT

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["payment_method"] = update.message.text
    reply_markup = ReplyKeyboardMarkup([["Zurück", "Weiter"]], one_time_keyboard=True)
    await update.message.reply_text("Drücke auf **Weiter**, um zur Zusammenfassung zu gelangen.", reply_markup=reply_markup)
    return FINALIZE_BOOKING

async def finalize_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_date = get_current_date()
    user_name = update.effective_user.username or update.effective_user.first_name
    photos = context.user_data.get("photos", [])
    summary = escape_markdown_v2(
        f"Du möchtest am **{selected_date}** zur Zeit **{context.user_data['selected_option'].splitlines()[0]}** teilnehmen.\n\n"
        f"Beschreibung: {context.user_data['description']}\n"
        f"Zahlungsmethode: {context.user_data['payment_method']}\n"
        f"Gesamtkosten: {context.user_data['selected_option'].splitlines()[1]}\n"
        f"Anzahlung: {context.user_data['selected_deposit']}\n\n"
        "Ohne Anzahlung innerhalb der nächsten 48 Stunden ist keine Teilnahme garantiert."
    )

    await update.message.reply_text(summary, parse_mode="MarkdownV2")
    for photo_id in photos:
        await update.message.reply_photo(photo_id)

    save_booking_with_photos(update.effective_user.id, selected_date, photos, context.user_data['payment_method'], context.user_data['selected_deposit'])

    admin_id = get_admin_id()
    if admin_id:
        await context.bot.send_message(chat_id=int(admin_id), text=f"Buchung von @{user_name}:\n\n{summary}", parse_mode="MarkdownV2")
        for photo_id in photos:
            await context.bot.send_photo(chat_id=int(admin_id), photo=photo_id)

    await update.message.reply_text("Deine Buchung wurde erfolgreich gespeichert. Vielen Dank!")
    return ConversationHandler.END

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        save_admin_id(context.args[0])
        await update.message.reply_text(f"Admin-ID wurde erfolgreich auf {context.args[0]} gesetzt.")
    else:
        await update.message.reply_text("Bitte gebe die Admin-ID an: /setadmin <Admin-ID>")

async def set_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        set_event_date(context.args[0])
        await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{context.args[0]}** gesetzt.")
    else:
        await update.message.reply_text("Bitte gib das Datum im Format 'YYYY-MM-DD' an: /setdate <Datum>")

if __name__ == "__main__":
    persistence = PicklePersistence(filepath="bot_data.pkl")
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("new", start)],
        states={
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            CONFIRM_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_selection)],
            UPLOAD_IMAGE: [MessageHandler(filters.PHOTO | filters.TEXT, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)],
            FINALIZE_BOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_booking)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("setadmin", set_admin))
    app.add_handler(CommandHandler("setdate", set_event))
    app.run_polling()