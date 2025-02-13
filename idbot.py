import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort für Admin-Zugang ---
ADMIN_PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("bot_manager.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            bot_name TEXT PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            bot_name TEXT,
            chat_id INTEGER,
            PRIMARY KEY (bot_name, chat_id),
            FOREIGN KEY (bot_name) REFERENCES bots(bot_name)
        )
    """)

    conn.commit()
    print("✅ Datenbank erfolgreich initialisiert.")
    return conn, cursor

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔑 Zugang erhalten", callback_data="enter_password")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🔒 Bitte bestätige dein Passwort, um fortzufahren:", reply_markup=reply_markup)

# --- Passwort-Eingabe ---
async def enter_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("🔑 Bitte sende dein Passwort als Nachricht.")
    context.user_data["awaiting_password"] = True

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == ADMIN_PASSWORD:
            context.user_data["authenticated"] = True
            await show_bots(update, context)  # Direkt zu den Bots weiterleiten
        else:
            await update.message.reply_text("❌ Falsches Passwort! Bitte versuche es erneut.")
        context.user_data["awaiting_password"] = False

# --- Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else update.message
    cursor.execute("SELECT bot_name FROM bots")
    bots = cursor.fetchall()

    if not bots:
        await query.message.reply_text("❌ Keine Bots in der Datenbank gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot[0], callback_data=f"manage_bot_{bot[0]}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü ---
async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "")
    context.user_data["selected_bot"] = bot_name  # Gewählten Bot speichern

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("➖ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="back_to_bots")]
    ]
    
    await query.message.edit_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppe zur Whitelist hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_add"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()

        try:
            cursor.execute("INSERT INTO allowed_groups (bot_name, chat_id) VALUES (?, ?)", (bot_name, chat_id))
            conn.commit()
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"⚠️ Diese Gruppe ist bereits für {bot_name} eingetragen.")

        context.user_data["awaiting_group_add"] = False

# --- Gruppe aus der Whitelist entfernen ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Sende die Gruppen-ID, die du entfernen möchtest.")
    context.user_data["awaiting_group_remove"] = True

async def process_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_remove"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()

        cursor.execute("DELETE FROM allowed_groups WHERE bot_name = ? AND chat_id = ?", (bot_name, chat_id))
        conn.commit()

        if cursor.rowcount > 0:
            await update.message.reply_text(f"✅ Gruppe {chat_id} wurde aus {bot_name} entfernt.")
        else:
            await update.message.reply_text(f"⚠️ Diese Gruppe existiert nicht für {bot_name}.")

        context.user_data["awaiting_group_remove"] = False

# --- Gruppen anzeigen ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]

    cursor.execute("SELECT chat_id FROM allowed_groups WHERE bot_name = ?", (bot_name,))
    groups = cursor.fetchall()

    if groups:
        response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n" + "\n".join(f"- `{group[0]}`" for group in groups)
    else:
        response = f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="manage_bot_" + bot_name)]
    ]))

# --- Zurück zum Bot-Menü ---
async def back_to_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_bots(update, context)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle & Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_group))

    # Inline-Menü Handler
    application.add_handler(CallbackQueryHandler(enter_password, pattern="^enter_password$"))
    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))
    application.add_handler(CallbackQueryHandler(back_to_bots, pattern="^back_to_bots$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()