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
    if context.user_data.get("authenticated"):  
        await update.message.reply_text("🔓 Du bist bereits angemeldet!", reply_markup=main_menu())
        return

    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um Zugriff zu erhalten:")
    context.user_data["awaiting_password"] = True  

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == PASSWORD:
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
            await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.", reply_markup=main_menu())
        else:
            await update.message.reply_text("❌ Falsches Passwort! Bitte starte erneut mit /start.")
            context.user_data["awaiting_password"] = False

# --- Hauptmenü ---
def main_menu():
    keyboard = [[InlineKeyboardButton("🔧 Bot verwalten", callback_data="show_bots")]]
    return InlineKeyboardMarkup(keyboard)

# --- Zugriffskontrolle ---
async def access_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("authenticated"):
        await update.message.reply_text("🚫 Zugriff verweigert! Bitte starte mit /start und gib das Passwort ein.")
        return False
    return True

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await access_control(update, context):
        return
    
    query = update.callback_query
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.message.edit_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])
    
    await query.message.edit_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

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
    
    await query.message.edit_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppe hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_add"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        try:
            cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1)", (chat_id,))
            conn.commit()
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde hinzugefügt.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"⚠️ Diese Gruppe ist bereits eingetragen.")

        context.user_data["awaiting_group_add"] = False

# --- Gruppe löschen mit Bestätigung ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.message.edit_text(f"❌ Keine Gruppen für {bot_name} eingetragen.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))
        return

    keyboard = [[InlineKeyboardButton(str(group[0]), callback_data=f"confirm_remove_{group[0]}")] for group in groups]
    keyboard.append([InlineKeyboardButton("🔙 Abbrechen", callback_data=f"manage_bot_{bot_name}")])
    await query.message.edit_text("🗑️ Wähle eine Gruppe zum Entfernen:", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("confirm_remove_", "")
    bot_name = context.user_data["selected_bot"]
    context.user_data["delete_group_id"] = chat_id 

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data="delete_group_confirmed")],
        [InlineKeyboardButton("❌ Nein, abbrechen", callback_data=f"manage_bot_{bot_name}")]
    ]
    
    await query.message.edit_text(f"⚠️ **Bist du sicher, dass du die Gruppe {chat_id} löschen möchtest?**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = context.user_data.get("delete_group_id")  
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    if chat_id:
        cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
        conn.commit()
        await query.message.edit_text(f"✅ Gruppe {chat_id} wurde gelöscht.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove_.*"))
    application.add_handler(CallbackQueryHandler(delete_group, pattern="^delete_group_confirmed$"))

    print("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()