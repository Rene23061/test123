import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Logging für Debugging ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO
)

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()

    # Falls "group_name" fehlt, hinzufügen
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

# --- Gruppen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id, group_name FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n"
    response += "\n".join(f"- `{group[0]}` | **{group[1]}**" for group in groups if group[1] is not None)

    await query.message.edit_text(response, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data=f"manage_bot_{bot_name}")]]))

# --- Gruppen hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Sende die **Gruppen-ID**.")
    context.user_data["awaiting_group_id"] = True

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return  # Verhindert Fehler bei Inline-Callbacks

    if context.user_data.get("awaiting_group_id"):
        chat_id = update.message.text.strip()
        if not chat_id.isdigit():
            await update.message.reply_text("⚠️ Ungültige Gruppen-ID! Bitte sende eine gültige Zahl.")
            return
        
        context.user_data["new_group_id"] = chat_id
        context.user_data["awaiting_group_id"] = False
        context.user_data["awaiting_group_name"] = True
        await update.message.reply_text("✍️ Sende jetzt den **Gruppennamen**.")
        return

    if context.user_data.get("awaiting_group_name"):
        bot_name = context.user_data.get("selected_bot")
        chat_id = context.user_data.get("new_group_id")
        group_name = update.message.text.strip()

        if not bot_name or not chat_id:
            await update.message.reply_text("⚠️ Ein interner Fehler ist aufgetreten. Versuche es erneut.")
            return

        column_name = f"allow_{bot_name}"

        try:
            cursor.execute(f"""
                INSERT INTO allowed_groups (chat_id, group_name, {column_name}) 
                VALUES (?, ?, 1) 
                ON CONFLICT(chat_id) DO UPDATE SET {column_name} = 1, group_name = ?
            """, (chat_id, group_name, group_name))
            conn.commit()
            await update.message.reply_text(
                f"✅ Gruppe **{group_name}** (`{chat_id}`) wurde für {bot_name} hinzugefügt.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück zum Hauptmenü", callback_data="show_bots")]])
            )
        except Exception as e:
            logging.error(f"Fehler beim Eintragen in die DB: {e}")
            await update.message.reply_text(f"⚠️ Fehler beim Eintragen: {e}")

        context.user_data["awaiting_group_name"] = False

# --- Bot starten ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))
    app.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    app.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    app.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    app.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    app.run_polling()

if __name__ == "__main__":
    main()