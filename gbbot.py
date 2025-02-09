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

def save_booking_with_photos(user_id: int, date: str, photos: list):
    try:
        # Öffne oder erstelle die Datei und füge eine neue Zeile hinzu
        with open(BOOKINGS_WITH_PHOTOS_FILE, "a") as file:
            photo_ids = ",".join(photos)
            file.write(f"{user_id}: {date}: {photo_ids}\n")
        logger.info(f"Buchung mit Fotos für Benutzer {user_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Buchung mit Fotos: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
                "Falls du kein Bild hochladen möchtest, schreibe bitte einfach **nein**."
            ),
            parse_mode="MarkdownV2"
        )
        return UPLOAD_IMAGE

async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data.setdefault("photos", [])

        # Gehe jedes hochgeladene Bild durch und speichere die höchste Auflösung
        for photo in update.message.photo:
            highest_res_photo = photo.file_id
            context.user_data["photos"].append(highest_res_photo)

        logger.info(f"Bild(er) erfolgreich hochgeladen. Anzahl gespeicherter Bilder: {len(context.user_data['photos'])}")

        await update.message.reply_text("Bild(er) gespeichert! Bitte beschreibe dich und deine Wünsche oder Vorlieben.")
        return ENTER_DESCRIPTION
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten des Bild-Uploads: {e}")
        await update.message.reply_text("Es gab ein Problem beim Hochladen der Bilder. Bitte versuche es erneut.")

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

    # Speichere die Buchung zusammen mit den Bild-IDs
    save_booking_with_photos(
        user_id=update.effective_user.id,
        date=selected_date,
        photos=context.user_data["photos"]
    )

    # Bilder an Benutzer senden
    if "photos" in context.user_data:
        for photo_id in context.user_data["photos"]:
            await update.message.reply_photo(photo_id)

    # Benutzername extrahieren
    user_name = update.effective_user.username if update.effective_user.username else update.effective_user.first_name

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
            text=f"Buchung von @{user_name}:\n\n{summary}",
            parse_mode="MarkdownV2"
        )
        # Bilder an Admin senden
        for photo_id in context.user_data["photos"]:
            await context.bot.send_photo(chat_id=int(admin_id), photo=photo_id)

    await update.message.reply_text("Deine Buchung wurde erfolgreich gespeichert. Vielen Dank!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Gespräch abgebrochen von Benutzer {update.effective_user.first_name}.")
    await update.message.reply_text(
        "Buchung abgebrochen. Du kannst jederzeit /start eingeben, um von vorne zu beginnen."
    )
    return ConversationHandler.END

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
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            CONFIRM_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_selection)],
            UPLOAD_IMAGE: [MessageHandler(filters.PHOTO, upload_image)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
            SELECT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_payment)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("setadmin", set_admin))

    logger.info("Bot wird gestartet...")
    app.run_polling()