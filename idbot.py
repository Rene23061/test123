import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Logging für Debugging ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort ---
PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()

    # Tabelle erstellen, falls nicht vorhanden
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Dynamisches Hinzufügen neuer Bot-Spalten ---
def add_bot_column(bot_name):
    column_name = f"allow_{bot_name}"
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE allowed_groups ADD COLUMN {column_name} INTEGER DEFAULT 0")
        conn.commit()

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um fortzufahren:")
    context.user_data["awaiting_password"] = True

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == PASSWORD:
            await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.")
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
            await show_bots(update, context)
        else:
            await update.message.reply_text("❌ Falsches Passwort! Zugriff verweigert.")
            context.user_data["awaiting_password"] = False

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("authenticated"):
        await update.message.reply_text("🚫 Zugriff verweigert! Bitte starte mit /start und gib das richtige Passwort ein.")
        return

    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(query, "edit_message_text"):
        await query.edit_message_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)
    else:
        await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü nach Auswahl eines Bots ---
async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "")
    context.user_data["selected_bot"] = bot_name  

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("➖ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_bots")]
    ]
    
    await query.edit_message_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppe zur Whitelist hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✍️ Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_add"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        try:
            add_bot_column(bot_name)  # Stelle sicher, dass die Spalte existiert
            cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1) ON CONFLICT(chat_id) DO UPDATE SET {column_name} = 1", (chat_id,))
            conn.commit()
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")
            logging.info(f"Gruppe {chat_id} zu {bot_name} hinzugefügt.")
        except sqlite3.Error as e:
            await update.message.reply_text(f"⚠️ Fehler: {e}")
            logging.error(f"Fehler beim Einfügen: {e}")

        context.user_data["awaiting_group_add"] = False

# --- Gruppe aus der Whitelist entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✍️ Sende die Gruppen-ID, die du entfernen möchtest.")
    context.user_data["awaiting_group_remove"] = True

async def process_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_remove"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        try:
            cursor.execute(f"UPDATE allowed_groups SET {column_name} = 0 WHERE chat_id = ?", (chat_id,))
            conn.commit()

            if cursor.rowcount > 0:
                await update.message.reply_text(f"✅ Gruppe {chat_id} wurde aus {bot_name} entfernt.")
                logging.info(f"Gruppe {chat_id} aus {bot_name} entfernt.")
            else:
                await update.message.reply_text(f"⚠️ Diese Gruppe existiert nicht für {bot_name}.")

        except sqlite3.Error as e:
            await update.message.reply_text(f"⚠️ Fehler: {e}")
            logging.error(f"Fehler beim Löschen: {e}")

        context.user_data["awaiting_group_remove"] = False

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_group))

    application.run_polling()

if __name__ == "__main__":
    main()