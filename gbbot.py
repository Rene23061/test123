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
SELECT_OPTION, CONFIRM_SELECTION, UPLOAD_IMAGE, ENTER_DESCRIPTION, SELECT_PAYMENT, CONFIRM_REBOOKING = range(6)

DATE_FILE = "event_date.txt"
USER_BOOKINGS_FILE = "user_bookings.txt"
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
    if os.path.exists(USER_BOOKINGS_FILE):
        with open(USER_BOOKINGS_FILE, "r") as file:
            for line in file:
                stored_user_id, stored_date = line.strip().split(": ")
                if str(user_id) == stored_user_id:
                    return stored_date
    return None

def save_booking(user_id: int, date: str):
    with open(USER_BOOKINGS_FILE, "a") as file:
        file.write(f"{user_id}: {date}\n")

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

async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "photos" not in context.user_data:
        context.user_data["photos"] = []

    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        context.user_data["photos"].append(photo_file_id)
        await update.message.reply_text("Bild gespeichert! Du kannst noch weitere Bilder hochladen oder **nein** schreiben, um fortzufahren.")
        return UPLOAD_IMAGE

    if update.message.text and update.message.text.lower() == "nein":
        await update.message.reply_text("Bilder-Upload abgeschlossen. Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    payment_options = [["Revolut", "PayPal"], ["Amazon Gutschein"]]
    reply_markup = ReplyKeyboardMarkup(payment_options, one_time_keyboard=True)
    await update.message.reply_text("Bitte wähle eine Zahlungsmethode aus:", reply_markup=reply_markup)
    return SELECT_PAYMENT

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    context.user_data["payment_method"] = payment_method

    selected_date = get_current_date()
    save_booking(update.effective_user.id, selected_date)

    # Bilder senden
    if "photos" in context.user_data:
        for photo_id in context.user_data["photos"]:
            await update.message.reply_photo(photo_id)

    summary = escape_markdown_v2(
        f"Du möchtest am **{selected_date}** zur Zeit **{context.user_data['selected_option'].splitlines()[0]}** teilnehmen.\n\n"
        f"Deine Beschreibung:\n{context.user_data['description']}\n\n"
        f"Zahlungsmethode: {payment_method}\n\n"
        "Ohne Anzahlung innerhalb der nächsten 48 Stunden ist keine Teilnahme garantiert."
    )

    await update.message.reply_text(summary, parse_mode="MarkdownV2")

    # Admin informieren
    admin_id = get_admin_id()
    if admin_id:
        await context.bot.send_message(
            chat_id=int(admin_id),
            text=f"Buchung von User {update.effective_user.first_name}:\n\n{summary}",
            parse_mode="MarkdownV2"
        )
        for photo_id in context.user_data["photos"]:
            await context.bot.send_photo(chat_id=int(admin_id), photo=photo_id)

    await update.message.reply_text("Deine Buchung wurde erfolgreich gespeichert. Vielen Dank!")
    return ConversationHandler.END

async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Entschuldigung, ich habe das nicht verstanden. Bitte wähle eine der verfügbaren Optionen oder benutze /cancel, um den Prozess abzubrechen."
    )

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Deine ID ist: {update.effective_user.id}")

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Bitte gib die Admin-ID an: /setadmin <Admin-ID>")
        return

    save_admin_id(context.args[0])
    await update.message.reply_text(f"Admin-ID wurde erfolgreich auf {context.args[0]} gesetzt.")

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
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)]
        },
        fallbacks=[MessageHandler(filters.ALL, fallback_message), CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("setadmin", set_admin))

    logger.info("Bot wird gestartet...")
    app.run_polling()