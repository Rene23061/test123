import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Logging aktivieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"

# Phasen der Buchung
SELECT_OPTION, ENTER_DESCRIPTION = range(2)

# Event-Datum speichern oder aktualisieren
def set_event_date(chat_id: str, new_date: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO event_settings (chat_id, event_date) 
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET event_date=excluded.event_date
        ''', (chat_id, new_date))
        connection.commit()
        connection.close()
        logger.info(f"Datum für Chat {chat_id} erfolgreich auf {new_date} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Datums: {e}")

# Event-Datum abrufen
def get_event_date(chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT event_date FROM event_settings WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        connection.close()
        return result[0] if result else "Noch kein Datum gesetzt"
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Datums: {e}")
        return "Fehler beim Laden des Datums"

# Gruppen-ID und Benutzer im privaten Chat verknüpfen
def save_group_link(user_chat_id: str, group_id: str):
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
        logger.error(f"Fehler beim Speichern der Gruppenverknüpfung: {e}")

# Verknüpfte Gruppen-ID abrufen
def get_linked_group_id(user_chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT group_chat_id FROM group_links WHERE user_chat_id = ?", (user_chat_id,))
        result = cursor.fetchone()
        connection.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der verknüpften Gruppen-ID: {e}")
        return None

# /start-Befehl
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        current_date = get_event_date(chat_id)
        await update.message.reply_text(
            f"Willkommen zur Veranstaltungsbuchung!\n"
            f"Das aktuelle Event-Datum ist: **{current_date}**",
            parse_mode="Markdown"
        )
    else:
        group_id = get_linked_group_id(chat_id)
        if group_id:
            current_date = get_event_date(group_id)
            await update.message.reply_text(
                f"Willkommen im privaten Chat!\n"
                f"Das Event-Datum der verknüpften Gruppe ist: **{current_date}**",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Es ist keine Gruppe verknüpft. Bitte verwende /id, um eine Gruppe zu verknüpfen.")

# /datum-Befehl
async def set_event_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if context.args:
            new_date = " ".join(context.args)
            if len(new_date.split(".")) == 3:
                set_event_date(chat_id, new_date)
                await update.message.reply_text(f"Das Veranstaltungsdatum wurde auf **{new_date}** geändert.", parse_mode="Markdown")
            else:
                await update.message.reply_text("Das Datum ist ungültig. Bitte gib es im Format TT.MM.JJJJ ein.")
        else:
            await update.message.reply_text("Bitte gib ein Datum im Format `/datum TT.MM.JJJJ` ein.")
    else:
        await update.message.reply_text("Dieser Befehl kann nur in der Gruppe verwendet werden.")

# /id-Befehl
async def get_and_save_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        group_id = str(update.effective_chat.id)
        await update.message.reply_text(f"Die aktuelle Gruppen-ID ist: **{group_id}**", parse_mode="Markdown")
    else:
        if context.args:
            group_id = context.args[0]
            user_chat_id = str(update.effective_chat.id)
            save_group_link(user_chat_id, group_id)
            await update.message.reply_text(f"Die Gruppe mit ID **{group_id}** wurde erfolgreich verknüpft.", parse_mode="Markdown")
        else:
            await update.message.reply_text("Bitte gib eine Gruppen-ID an: `/id [Gruppen-ID]`")

# Private Buchung starten
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_id = str(update.effective_chat.id)
    group_id = get_linked_group_id(user_chat_id)
    if not group_id:
        await update.message.reply_text("Es ist keine Gruppe verknüpft. Bitte verknüpfe zuerst eine Gruppe mit /id.")
        return ConversationHandler.END

    options = [["Option 1", "Option 2"]]
    reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)
    await update.message.reply_text(
        "Bitte wähle eine Option für deine Buchung:", reply_markup=reply_markup
    )
    return SELECT_OPTION

async def select_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['selected_option'] = update.message.text
    await update.message.reply_text("Gib bitte eine Beschreibung für deine Buchung ein.")
    return ENTER_DESCRIPTION

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    user_chat_id = str(update.effective_chat.id)
    group_id = get_linked_group_id(user_chat_id)
    selected_option = context.user_data['selected_option']

    save_booking(group_id, selected_option, description)
    await update.message.reply_text(f"Buchung gespeichert:\n- Option: {selected_option}\n- Beschreibung: {description}")
    return ConversationHandler.END

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
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Buchung: {e}")

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("datum", set_event_date_command))
    app.add_handler(CommandHandler("id", get_and_save_chat_id))
    app.add_handler(conv_handler)

    logger.info("Bot wird gestartet...")
    app.run_polling()