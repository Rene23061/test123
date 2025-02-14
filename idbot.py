import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort ---
PASSWORD = "Shorty2306"

# --- Logging für Debugging ---
logging.basicConfig(filename="debug_log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

def log_message(message):
    with open("debug_log.txt", "a") as log_file:
        log_file.write(message + "\n")
    logging.info(message)

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = init_db()

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message("🔑 /start wurde aufgerufen.")
    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um fortzufahren:")
    context.user_data["awaiting_password"] = True

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        log_message(f"🔑 Passwortprüfung gestartet mit Eingabe: {update.message.text}")
        if update.message.text == PASSWORD:
            await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.")
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
            await show_bots(update, context)
        else:
            await update.message.reply_text("❌ Falsches Passwort! Zugriff verweigert.")
            context.user_data["awaiting_password"] = False
    elif context.user_data.get("awaiting_group_add"):
        await process_add_group(update, context)

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("authenticated"):
        await update.message.reply_text("🚫 Zugriff verweigert! Bitte starte mit /start und gib das richtige Passwort ein.")
        return

    log_message("📌 show_bots() wurde aufgerufen.")
    
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]
    bots = [col.replace("allow_", "") for col in columns]

    log_message(f"🤖 Gefundene Bots: {bots}")

    if not bots:
        await update.message.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü nach Auswahl eines Bots ---
async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "")
    context.user_data["selected_bot"] = bot_name

    log_message(f"⚙️ manage_bot() aufgerufen für {bot_name}")

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
    log_message("🔍 add_group() wurde aufgerufen.")

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_add"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        log_message(f"📝 Eintragen: {chat_id} → {column_name}")

        try:
            cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1) ON CONFLICT(chat_id) DO UPDATE SET {column_name} = 1", (chat_id,))
            conn.commit()
            log_message(f"✅ Nach Einfügen: {cursor.execute(f'SELECT * FROM allowed_groups WHERE chat_id = ?', (chat_id,)).fetchone()}")
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")
        except sqlite3.IntegrityError as e:
            log_message(f"⚠️ Datenbankfehler: {str(e)}")
            await update.message.reply_text(f"⚠️ Diese Gruppe ist bereits für {bot_name} eingetragen.")

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

        log_message(f"❌ Löschen: {chat_id} aus {column_name}")

        cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
        conn.commit()

        if cursor.rowcount > 0:
            log_message(f"✅ {chat_id} erfolgreich entfernt.")
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde aus {bot_name} entfernt.")
        else:
            log_message(f"⚠️ {chat_id} war nicht vorhanden.")
            await update.message.reply_text(f"⚠️ Diese Gruppe existiert nicht für {bot_name}.")

        context.user_data["awaiting_group_remove"] = False

# --- Gruppen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    log_message(f"📜 list_groups() für {bot_name}: {groups}")

    response = f"📋 Erlaubte Gruppen für {bot_name}:\n" + "\n".join(f"- `{group[0]}`" for group in groups) if groups else f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="manage_bot_" + bot_name)]
    ]))

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.run_polling()

if __name__ == "__main__":
    main()