import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
DB_PATH = "/root/cpkiller/whitelist.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY,
            allow_sbot INTEGER DEFAULT 0,
            allow_idbot INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Startbefehl mit Inline-Buttons ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Erlaubte Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group"),
         InlineKeyboardButton("❌ Gruppe entfernen", callback_data="remove_group")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔧 Verwaltungsmenü:", reply_markup=reply_markup)

# --- Gruppen auflisten ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cursor.execute("SELECT chat_id, allow_sbot, allow_idbot FROM allowed_groups")
    groups = cursor.fetchall()

    if not groups:
        await query.answer("❌ Keine erlaubten Gruppen!")
        return

    response = "📋 **Erlaubte Gruppen:**\n"
    for chat_id, allow_sbot, allow_idbot in groups:
        bots = []
        if allow_sbot:
            bots.append("🤖 sbot")
        if allow_idbot:
            bots.append("🆔 idbot")
        response += f"- `{chat_id}` ({', '.join(bots)})\n"

    await query.message.edit_text(response, parse_mode="Markdown")

# --- Gruppe hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("➕ sbot", callback_data="add_sbot"),
         InlineKeyboardButton("➕ idbot", callback_data="add_idbot")],
        [InlineKeyboardButton("➕ Beide", callback_data="add_both")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔹 Wähle den Bot, den du einer Gruppe hinzufügen möchtest:", reply_markup=reply_markup)

# --- Gruppe entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cursor.execute("SELECT chat_id FROM allowed_groups")
    groups = cursor.fetchall()

    if not groups:
        await query.answer("❌ Keine erlaubten Gruppen zum Entfernen!")
        return

    keyboard = [
        [InlineKeyboardButton(f"❌ {chat_id}", callback_data=f"remove_{chat_id}")] for (chat_id,) in groups
    ]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔻 Wähle die Gruppe, die du entfernen möchtest:", reply_markup=reply_markup)

# --- Callback für Gruppenänderungen ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data

    if action == "list_groups":
        await list_groups(update, context)
    elif action == "add_group":
        await add_group(update, context)
    elif action == "remove_group":
        await remove_group(update, context)
    elif action.startswith("add_"):
        bot_type = action.split("_")[1]
        context.user_data["adding_bot"] = bot_type
        await query.message.edit_text("🆔 Sende mir die Gruppen-ID, die du hinzufügen möchtest.")
    elif action.startswith("remove_"):
        chat_id = action.split("_")[1]
        cursor.execute("DELETE FROM allowed_groups WHERE chat_id = ?", (chat_id,))
        conn.commit()
        await query.answer("✅ Gruppe entfernt!")
        await remove_group(update, context)

# --- Verarbeitet die gesendete Gruppen-ID ---
async def receive_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "adding_bot" not in context.user_data:
        return

    bot_type = context.user_data["adding_bot"]
    chat_id = update.message.text.strip()

    allow_sbot = 1 if bot_type in ["sbot", "both"] else 0
    allow_idbot = 1 if bot_type in ["idbot", "both"] else 0

    try:
        cursor.execute("""
            INSERT INTO allowed_groups (chat_id, allow_sbot, allow_idbot) 
            VALUES (?, ?, ?) 
            ON CONFLICT(chat_id) DO UPDATE SET allow_sbot = ?, allow_idbot = ?
        """, (chat_id, allow_sbot, allow_idbot, allow_sbot, allow_idbot))

        conn.commit()
        await update.message.reply_text(f"✅ Gruppe `{chat_id}` wurde für `{bot_type}` hinzugefügt.", parse_mode="Markdown")

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Diese Gruppen-ID ist bereits gespeichert.")

    del context.user_data["adding_bot"]

# --- Hauptfunktion ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_id))

    print("🤖 ID-Bot mit Inline-Menü gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()