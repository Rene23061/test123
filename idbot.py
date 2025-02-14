import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = init_db()

# --- Logging-Funktion für Debugging ---
def log_message(message):
    with open("debug_log.txt", "a") as log_file:
        log_file.write(message + "\n")
    print(message)

# --- /start-Befehl ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message("🚀 /start wurde aufgerufen.")
    await show_bots(update, context)

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message("📌 show_bots() wurde aufgerufen.")

    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    log_message(f"🤖 Gefundene Bots: {bots}")

    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü ---
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

# --- Gruppe aus der Whitelist entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✍️ Sende die Gruppen-ID, die du entfernen möchtest.")
    context.user_data["awaiting_group_remove"] = True
    log_message("🔎 remove_group() wurde aufgerufen.")

async def process_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_remove"):
        bot_name = context.user_data.get("selected_bot")
        if not bot_name:
            log_message("⚠️ Kein Bot ausgewählt!")
            await update.message.reply_text("⚠️ Fehler: Kein Bot ausgewählt!")
            return

        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        log_message(f"🗑️ Entfernen: {chat_id} → {column_name}")

        cursor.execute(f"UPDATE allowed_groups SET {column_name} = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()

        cursor.execute(f"SELECT {column_name} FROM allowed_groups WHERE chat_id = ?", (chat_id,))
        updated_data = cursor.fetchone()

        if updated_data and updated_data[0] == 0:
            log_message(f"✅ Nach Entfernen in DB: {updated_data}")
            keyboard = [[InlineKeyboardButton("🔙 Zurück zur Verwaltung", callback_data=f"manage_bot_{bot_name}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde aus {bot_name} entfernt.", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"⚠️ Diese Gruppe existiert nicht oder war nicht eingetragen.")

        context.user_data["awaiting_group_remove"] = False

# --- Gruppen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    log_message(f"🔍 DEBUG: Gruppenabfrage für {bot_name}: {groups}")

    if groups:
        response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n" + "\n".join(f"- `{group[0]}`" for group in groups)
    else:
        response = f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="manage_bot_" + bot_name)]
    ]))

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))

    log_message("🚀 Bot wurde gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()