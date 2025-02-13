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

# --- Startmenü mit Bot-Auswahl ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤖 sbot", callback_data="bot_sbot")],
        [InlineKeyboardButton("🆔 idbot", callback_data="bot_idbot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔧 Wähle einen Bot:", reply_markup=reply_markup)

# --- Menü für sbot oder idbot anzeigen ---
async def show_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = query.data.split("_")[1]  # sbot oder idbot
    context.user_data["selected_bot"] = bot_type  # Speichern, welcher Bot gewählt wurde

    keyboard = [
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("❌ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="back_to_bots")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"🔹 Verwaltung für `{bot_type}`:", reply_markup=reply_markup)

# --- Gruppen auflisten ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    if not bot_type:
        await query.answer("❌ Kein Bot ausgewählt!")
        return

    column = "allow_sbot" if bot_type == "sbot" else "allow_idbot"
    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.answer(f"❌ Keine erlaubten Gruppen für `{bot_type}`!")
        return

    response = f"📋 **Erlaubte Gruppen für `{bot_type}`:**\n"
    response += "\n".join(f"- `{chat_id[0]}`" for chat_id in groups)

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data=f"bot_{bot_type}")]
    ]))

# --- Gruppe hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    if not bot_type:
        await query.answer("❌ Kein Bot ausgewählt!")
        return

    context.user_data["adding_group"] = bot_type
    await query.message.edit_text("🆔 Sende mir die Gruppen-ID, die du hinzufügen möchtest.")

# --- Gruppe entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    if not bot_type:
        await query.answer("❌ Kein Bot ausgewählt!")
        return

    column = "allow_sbot" if bot_type == "sbot" else "allow_idbot"
    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.answer(f"❌ Keine erlaubten Gruppen für `{bot_type}`!")
        return

    keyboard = [
        [InlineKeyboardButton(f"❌ {chat_id[0]}", callback_data=f"remove_{chat_id[0]}")] for chat_id in groups
    ]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"bot_{bot_type}")])
    
    await query.message.edit_text("🔻 Wähle die Gruppe, die du entfernen möchtest:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppen-ID speichern ---
async def receive_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_type = context.user_data.get("adding_group")

    if not bot_type:
        return

    chat_id = update.message.text.strip()
    column = "allow_sbot" if bot_type == "sbot" else "allow_idbot"

    try:
        cursor.execute(f"""
            INSERT INTO allowed_groups (chat_id, {column}) 
            VALUES (?, 1) 
            ON CONFLICT(chat_id) DO UPDATE SET {column} = 1
        """, (chat_id,))
        conn.commit()

        await update.message.reply_text(f"✅ Gruppe `{chat_id}` wurde für `{bot_type}` hinzugefügt.", parse_mode="Markdown")

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Diese Gruppen-ID ist bereits gespeichert.")

    del context.user_data["adding_group"]

# --- Gruppe aus der Datenbank entfernen ---
async def remove_group_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[1]
    bot_type = context.user_data.get("selected_bot")

    if not bot_type:
        await query.answer("❌ Kein Bot ausgewählt!")
        return

    column = "allow_sbot" if bot_type == "sbot" else "allow_idbot"
    cursor.execute(f"UPDATE allowed_groups SET {column} = 0 WHERE chat_id = ?", (chat_id,))
    conn.commit()

    await query.answer(f"✅ Gruppe `{chat_id}` wurde entfernt.")
    await remove_group(update, context)  # Menü aktualisieren

# --- Zurück zum Bot-Menü ---
async def back_to_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# --- Hauptfunktion ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_bot_menu, pattern="^bot_"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(remove_group_confirm, pattern="^remove_"))
    application.add_handler(CallbackQueryHandler(back_to_bots, pattern="^back_to_bots$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_id))

    print("🤖 ID-Bot mit Inline-Menü gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()