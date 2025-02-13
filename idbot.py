import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwortschutz ---
PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
DB_PATH = "/root/cpkiller/whitelist.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY,
            allow_sbot INTEGER DEFAULT 0,
            allow_cpbot INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Startmenü ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔧 Verwaltung starten", callback_data="enter_password")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Willkommen! Wähle eine Aktion:", reply_markup=reply_markup)

# --- Passwort-Abfrage starten ---
async def ask_for_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["awaiting_password"] = True
    await query.message.edit_text("🔐 Bitte gib das Passwort ein:")

# --- Passwort-Eingabe prüfen ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == PASSWORD:
            context.user_data["authenticated"] = True
            del context.user_data["awaiting_password"]
            await show_bot_selection(update)
        else:
            await update.message.reply_text("❌ Falsches Passwort. Versuch es erneut.")

# --- Bot-Auswahl-Menü (erscheint erst nach Passwort) ---
async def show_bot_selection(update: Update):
    keyboard = [
        [InlineKeyboardButton("🤖 sbot", callback_data="bot_sbot")],
        [InlineKeyboardButton("🛡 cpbot", callback_data="bot_cpbot")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("🔧 Wähle einen Bot:", reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text("🔧 Wähle einen Bot:", reply_markup=reply_markup)

# --- Menü für sbot oder cpbot ---
async def show_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = query.data.split("_")[1]
    context.user_data["selected_bot"] = bot_type  

    keyboard = [
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("❌ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="back_to_bots")]
    ]
    await query.message.edit_text(f"🔹 Verwaltung für `{bot_type}`:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppen auflisten ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    column = "allow_sbot" if bot_type == "sbot" else "allow_cpbot"
    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column} = 1")
    groups = cursor.fetchall()

    if not groups:
        response = f"❌ Keine erlaubten Gruppen für `{bot_type}`!"
    else:
        response = f"📋 **Erlaubte Gruppen für `{bot_type}`:**\n" + "\n".join(f"- `{chat_id[0]}`" for chat_id in groups)

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data=f"bot_{bot_type}")]
    ]))

# --- Gruppe hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    context.user_data["adding_group"] = bot_type
    await query.message.edit_text("🆔 Sende mir die Gruppen-ID, die du hinzufügen möchtest.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Abbrechen", callback_data=f"bot_{bot_type}")]
    ]))

# --- Gruppe entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_type = context.user_data.get("selected_bot")

    column = "allow_sbot" if bot_type == "sbot" else "allow_cpbot"
    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.message.edit_text(f"❌ Keine erlaubten Gruppen für `{bot_type}`!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Zurück", callback_data=f"bot_{bot_type}")]
        ]))
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
    column = "allow_sbot" if bot_type == "sbot" else "allow_cpbot"

    try:
        cursor.execute(f"""
            INSERT INTO allowed_groups (chat_id, {column}) 
            VALUES (?, 1) 
            ON CONFLICT(chat_id) DO UPDATE SET {column} = 1
        """, (chat_id,))
        conn.commit()

        await update.message.reply_text(f"✅ Gruppe `{chat_id}` wurde für `{bot_type}` hinzugefügt.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Zurück", callback_data=f"bot_{bot_type}")]
        ]))

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Diese Gruppen-ID ist bereits gespeichert.")

    del context.user_data["adding_group"]

# --- Zurück zum Startmenü ---
async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# --- Zurück zur Bot-Auswahl ---
async def back_to_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_bot_selection(update)

# --- Hauptfunktion ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(ask_for_password, pattern="^enter_password$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(CallbackQueryHandler(show_bot_menu, pattern="^bot_"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    application.add_handler(CallbackQueryHandler(back_to_bots, pattern="^back_to_bots$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_id))

    print("🤖 ID-Bot mit Passwortschutz gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()