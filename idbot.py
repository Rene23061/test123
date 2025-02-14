import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort ---
PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = init_db()

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um fortzufahren:")
    context.user_data["awaiting_password"] = True  # Wartet auf Passwort-Eingabe

# --- Passwortprüfung und Login ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == PASSWORD:
            await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.")
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
            await show_bots(update, context)  # Direkt zur Bot-Auswahl
        else:
            await update.message.reply_text("❌ Falsches Passwort! Zugriff verweigert.")

# --- Alle Bots anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("authenticated"):
        await update.message.reply_text("🚫 Zugriff verweigert! Starte mit /start und gib das richtige Passwort ein.")
        return

    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])

    if isinstance(query, Update) or not hasattr(query, "edit_message_text"):
        await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

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

    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="manage_bot_" + bot_name)]
    ]))

# --- Gruppe hinzufügen ---
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
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde hinzugefügt.")
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"⚠️ Diese Gruppe ist bereits eingetragen.")

        context.user_data["awaiting_group_add"] = False

# --- Gruppe entfernen ---
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

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("confirm_remove_", "")
    bot_name = context.user_data["selected_bot"]
    context.user_data["delete_group_id"] = chat_id 

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data="delete_group_confirmed")],
        [InlineKeyboardButton("❌ Nein, abbrechen", callback_data=f"manage_bot_{bot_name}")]
    ]
    
    await query.edit_message_text(f"⚠️ **Bist du sicher, dass du die Gruppe {chat_id} löschen möchtest?**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = context.user_data.get("delete_group_id")  
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    if chat_id:
        cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
        conn.commit()
        await query.edit_message_text(f"✅ Gruppe {chat_id} wurde gelöscht.")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove_.*"))
    application.add_handler(CallbackQueryHandler(delete_group, pattern="^delete_group_confirmed$"))

    print("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()