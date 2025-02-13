import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Bot-Token für den Admin-Bot ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"
PASSWORD = "Shorty2306"

# --- Logging aktivieren ---
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Verbindung zur SQLite-Datenbank herstellen ---
def connect_db():
    return sqlite3.connect("/root/cpkiller/bot_manager.db", check_same_thread=False)

# --- Passwortabfrage beim Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet den Bot mit einer Passwortabfrage."""
    context.user_data["waiting_for_password"] = True
    await update.message.reply_text("🔒 Bitte gib das Passwort ein:")

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Überprüft das Passwort."""
    if "waiting_for_password" in context.user_data and context.user_data["waiting_for_password"]:
        if update.message.text.strip() == PASSWORD:
            context.user_data["waiting_for_password"] = False
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ Falsches Passwort! Versuch es erneut.")

# --- Hauptmenü anzeigen ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Liste der Bots mit Buttons an."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT bot_id, name FROM bots")
    bots = cursor.fetchall()
    conn.close()

    keyboard = [[InlineKeyboardButton(bot[1], callback_data=f"bot_{bot[0]}")] for bot in bots]
    keyboard.append([InlineKeyboardButton("➕ Bot hinzufügen", callback_data="add_bot")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 **Deine Bots:**", reply_markup=reply_markup)

# --- Funktion zum Hinzufügen eines neuen Bots ---
async def add_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✍️ Bitte sende mir den **Benutzernamen** des neuen Bots (`@sbot`).")
    context.user_data["waiting_for_bot_name"] = True

# --- Speichert den Bot-Namen und fragt nach dem Token ---
async def save_bot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for_bot_name" in context.user_data and context.user_data["waiting_for_bot_name"]:
        bot_name = update.message.text.strip()

        if not bot_name.startswith("@"):
            await update.message.reply_text("❌ Der Bot-Name muss mit `@` beginnen!")
            return

        context.user_data["new_bot_name"] = bot_name
        context.user_data["waiting_for_bot_name"] = False
        context.user_data["waiting_for_bot_token"] = True

        await update.message.reply_text("✍️ Jetzt bitte das **Bot-Token** senden.")

# --- Speichert das Bot-Token in der Datenbank ---
async def save_bot_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for_bot_token" in context.user_data and context.user_data["waiting_for_bot_token"]:
        bot_token = update.message.text.strip()
        bot_name = context.user_data["new_bot_name"]

        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO bots (name, token) VALUES (?, ?)", (bot_name, bot_token))
            conn.commit()
            await update.message.reply_text(f"✅ Der Bot `{bot_name}` wurde erfolgreich hinzugefügt!")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ Ein Bot mit diesem Namen oder Token existiert bereits!")
        conn.close()

        # Reset des Status
        context.user_data["waiting_for_bot_token"] = False
        context.user_data.pop("new_bot_name", None)

# --- Callback-Handler für Inline-Buttons ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_bot":
        await add_bot(update, context)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_bot_name))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_bot_token))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("🤖 ID-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()