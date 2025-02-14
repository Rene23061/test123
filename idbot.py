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

# ===================== /start-Befehl =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Willkommen! Wähle einen Bot zur Verwaltung:")
    await show_bots(update, context)

# ===================== Bot-Auswahl-Menü =====================
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

    if isinstance(query, Update) or not hasattr(query, "edit_message_text"):
        await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

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

# ===================== Gruppe entfernen - NEUES MENÜ =====================
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.edit_message_text(f"❌ Keine Gruppen für {bot_name} vorhanden.")
        return
    
    keyboard = [
        [InlineKeyboardButton(f"🗑 {group[0]}", callback_data=f"confirm_delete_{group[0]}")]
        for group in groups
    ]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")])
    
    await query.edit_message_text(f"📋 Wähle eine Gruppe zum Löschen:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===================== Bestätigung zum Löschen =====================
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("confirm_delete_", "")
    context.user_data["delete_chat_id"] = chat_id

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data="delete_group")],
        [InlineKeyboardButton("❌ Nein, zurück", callback_data=f"remove_group")]
    ]
    
    await query.edit_message_text(f"❗ Willst du wirklich die Gruppe `{chat_id}` löschen?", 
                                  parse_mode="Markdown", 
                                  reply_markup=InlineKeyboardMarkup(keyboard))

# ===================== Gruppe endgültig löschen =====================
async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    chat_id = context.user_data.get("delete_chat_id")
    column_name = f"allow_{bot_name}"

    if not chat_id:
        await query.edit_message_text("❌ Fehler: Keine Gruppen-ID gefunden.")
        return

    cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
    conn.commit()

    if cursor.rowcount > 0:
        await query.edit_message_text(f"✅ Gruppe `{chat_id}` erfolgreich entfernt!", parse_mode="Markdown")
    else:
        await query.edit_message_text(f"⚠️ Fehler beim Löschen von `{chat_id}`.", parse_mode="Markdown")

    # Zurück zum Gruppen-Lösch-Menü
    await remove_group(update, context)

# ===================== Bot Initialisierung =====================
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    
    # Callback-Handler für Menüführung
    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern="^confirm_delete_.*"))
    application.add_handler(CallbackQueryHandler(delete_group, pattern="^delete_group$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()