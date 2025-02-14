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

# --- /start-Befehl ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Willkommen! Wähle eine Aktion:", reply_markup=main_menu())

# --- Hauptmenü ---
def main_menu():
    keyboard = [[InlineKeyboardButton("🔧 Bot verwalten", callback_data="show_bots")]]
    return InlineKeyboardMarkup(keyboard)

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(query, "message"):
        await query.message.edit_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)
    else:
        await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü ---
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
            cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1)", (chat_id,))
            conn.commit()
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"⚠️ Diese Gruppe ist bereits für {bot_name} eingetragen.")

        context.user_data["awaiting_group_add"] = False

# --- Gruppe aus der Whitelist entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.edit_message_text(f"❌ Keine Gruppen für {bot_name} eingetragen.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))
        return

    keyboard = [[InlineKeyboardButton(str(group[0]), callback_data=f"confirm_remove_{group[0]}")] for group in groups]
    keyboard.append([InlineKeyboardButton("🔙 Abbrechen", callback_data=f"manage_bot_{bot_name}")])
    await query.edit_message_text("🗑️ Wähle eine Gruppe zum Entfernen:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Bestätigung für das Löschen ---
async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("confirm_remove_", "")
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
    conn.commit()

    await query.edit_message_text(f"✅ Gruppe {chat_id} wurde aus {bot_name} entfernt.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))

# --- Gruppen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if groups:
        response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n" + "\n".join(f"- `{group[0]}`" for group in groups)
    else:
        response = f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove_.*"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()