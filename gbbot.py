import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"
SELECT_OPTION, ENTER_DESCRIPTION = range(2)

def get_linked_group_id(user_chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT group_chat_id FROM group_links WHERE user_chat_id = ?", (user_chat_id,))
        result = cursor.fetchone()
        connection.close()

        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der verknüpften Gruppen-ID: {e}")
        return None

def save_booking(chat_id: str, selected_option: str, description: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO bookings (chat_id, selected_option, description)
            VALUES (?, ?, ?)
        ''', (chat_id, selected_option, description))
        
        connection.commit()
        connection.close()
        logger.info(f"Buchung für Chat {chat_id} erfolgreich gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Buchung: {e}")

# Start der privaten Buchung
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_id = str(update.effective_chat.id)
    group_id = get_linked_group_id(user_chat_id)

    if not group_id:
        await update.message.reply_text("Es ist keine Gruppe mit dir verknüpft. Bitte verknüpfe zuerst eine Gruppe mit /id.")
        return ConversationHandler.END

    # Optionen zur Auswahl anzeigen
    options = [["Option 1", "Option 2"]]
    reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)
    await update.message.reply_text(
        f"Du buchst für das Event der Gruppe {group_id}.\nBitte wähle eine Option:",
        reply_markup=reply_markup
    )
    return SELECT_OPTION

# Ausgewählte Option verarbeiten
async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_option = update.message.text
    context.user_data['selected_option'] = selected_option
    await update.message.reply_text(f"Du hast '{selected_option}' gewählt. Bitte gib eine Beschreibung ein.")
    return ENTER_DESCRIPTION

# Beschreibung der Buchung empfangen
async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    user_chat_id = str(update.effective_chat.id)
    group_id = get_linked_group_id(user_chat_id)

    if not group_id:
        await update.message.reply_text("Es ist keine verknüpfte Gruppe gefunden. Buchung abgebrochen.")
        return ConversationHandler.END

    selected_option = context.user_data['selected_option']
    save_booking(group_id, selected_option, description)

    await update.message.reply_text(f"Deine Buchung wurde gespeichert:\n- Option: {selected_option}\n- Beschreibung: {description}")
    return ConversationHandler.END

# /id-Befehl zur Verknüpfung der Gruppe mit einem privaten Benutzer
async def get_and_save_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        group_id = str(update.effective_chat.id)
        await update.message.reply_text(f"Die aktuelle Gruppen-ID ist: **{group_id}**", parse_mode="Markdown")
    else:
        if context.args:
            group_id = context.args[0]
            user_chat_id = str(update.effective_chat.id)
            save_group_id(user_chat_id, group_id)
            await update.message.reply_text(f"Die Gruppe mit ID **{group_id}** wurde erfolgreich verknüpft.", parse_mode="Markdown")
        else:
            await update.message.reply_text("Bitte gib eine Gruppen-ID an: `/id [Gruppen-ID]`")

def save_group_id(user_chat_id: str, group_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO group_links (user_chat_id, group_chat_id)
            VALUES (?, ?)
        ''', (user_chat_id, group_id))
        
        connection.commit()
        connection.close()
        logger.info(f"Verknüpfung zwischen Benutzer {user_chat_id} und Gruppe {group_id} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Gruppen-ID: {e}")

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("buchen", start_booking)],
        states={
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_option)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("id", get_and_save_chat_id))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()