import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token (TESTTOKEN) ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Falls Spalte group_name noch nicht existiert, fügen wir sie hinzu
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall()]
    if "group_name" not in columns:
        cursor.execute("ALTER TABLE allowed_groups ADD COLUMN group_name TEXT;")
        conn.commit()
    
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
    bot_name = query.data.replace("manage_bot_", "").lower()
    context.user_data["selected_bot"] = bot_name  

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("➖ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_bots")]
    ]
    
    await query.message.edit_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppe zur Whitelist hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Sende die Gruppen-ID und den Namen.\n**Format:** `-1001234567890 Meine Gruppe`", parse_mode="Markdown")
    context.user_data["awaiting_group_add"] = True

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_add"):
        bot_name = context.user_data["selected_bot"]
        text = update.message.text.strip()

        try:
            chat_id, group_name = text.split(" ", 1)
        except ValueError:
            await update.message.reply_text("⚠️ Fehler: Bitte gib die Gruppen-ID und den Namen ein.\nBeispiel: `-1001234567890 Meine Gruppe`", parse_mode="Markdown")
            return

        column_name = f"allow_{bot_name.lower()}"

        try:
            cursor.execute(f"""
                INSERT INTO allowed_groups (chat_id, group_name, {column_name}) 
                VALUES (?, ?, 1) 
                ON CONFLICT(chat_id) DO UPDATE SET {column_name} = 1, group_name = ?
            """, (chat_id, group_name, group_name))
            conn.commit()
            await update.message.reply_text(f"✅ Gruppe **{group_name}** (`{chat_id}`) wurde für {bot_name} hinzugefügt.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Fehler beim Eintragen: {e}")

        context.user_data["awaiting_group_add"] = False

# --- Gruppen mit Namen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name.lower()}"

    cursor.execute(f"SELECT chat_id, group_name FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if groups:
        response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n"
        response += "\n".join(f"- `{group[0]}` | **{group[1]}**" for group in groups if group[1] is not None)
    else:
        response = f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))

# --- Gruppen mit Namen entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name.lower()}"

    cursor.execute(f"SELECT chat_id, group_name FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if not groups:
        await query.message.edit_text(f"❌ Keine Gruppen für {bot_name} eingetragen.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))
        return

    keyboard = [[InlineKeyboardButton(f"{group[1]} ({group[0]})", callback_data=f"confirm_remove_{group[0]}")] for group in groups]
    keyboard.append([InlineKeyboardButton("🔙 Abbrechen", callback_data=f"manage_bot_{bot_name}")])
    await query.message.edit_text("🗑️ Wähle eine Gruppe zum Entfernen:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = context.user_data.get("delete_group_id")
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name.lower()}"

    if chat_id:
        cursor.execute("SELECT group_name FROM allowed_groups WHERE chat_id = ?", (chat_id,))
        group_name = cursor.fetchone()

        cursor.execute(f"UPDATE allowed_groups SET {column_name} = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()

        await query.message.edit_text(f"✅ Gruppe **{group_name[0]}** (`{chat_id}`) wurde für {bot_name} entfernt.", parse_mode="Markdown")
    else:
        await query.message.edit_text("⚠️ Fehler: Keine Gruppen-ID gefunden.")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(delete_group, pattern="^delete_group_confirmed$"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()