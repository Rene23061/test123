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
    await show_bots(update, context)

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
    
    await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü nach Auswahl eines Bots ---
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
        print("🔍 Funktion `process_add_group` wurde aufgerufen!")  # DEBUG

        bot_name = context.user_data.get("selected_bot")
        chat_id = update.message.text.strip() if update.message else None

        if not chat_id:
            print("❌ Fehler: `chat_id` ist leer!")  # DEBUG
            await update.message.reply_text("⚠️ Fehler: Ungültige Gruppen-ID!")
            return

        column_name = f"allow_{bot_name}"
        print(f"📌 Versuche, Gruppe {chat_id} für Bot {bot_name} einzutragen...")  # DEBUG

        try:
            cursor.execute("PRAGMA table_info(allowed_groups);")
            columns = [col[1] for col in cursor.fetchall()]
            if column_name not in columns:
                print(f"❌ Fehler: Spalte {column_name} existiert nicht!")  # DEBUG
                await update.message.reply_text(f"❌ Fehler: Spalte {column_name} existiert nicht in der Datenbank!")
                return

            cursor.execute("SELECT chat_id FROM allowed_groups WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()

            if result:
                print(f"🔄 Aktualisiere existierende Gruppe {chat_id} für {bot_name}")  # DEBUG
                cursor.execute(f"UPDATE allowed_groups SET {column_name} = 1 WHERE chat_id = ?", (chat_id,))
            else:
                print(f"✅ Neue Gruppe {chat_id} wird hinzugefügt für {bot_name}")  # DEBUG
                cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1)", (chat_id,))

            conn.commit()
            print(f"✅ Gruppe {chat_id} erfolgreich gespeichert!")  # DEBUG
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")

        except sqlite3.Error as e:
            print(f"⚠️ Fehler in der Datenbank: {e}")  # DEBUG
            await update.message.reply_text(f"⚠️ Fehler beim Einfügen in die Datenbank: {e}")

        context.user_data["awaiting_group_add"] = False

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))
    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()