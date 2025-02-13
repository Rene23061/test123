import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"
PASSWORD = "Shorty2306"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("bot_manager.db", check_same_thread=False)
    cursor = conn.cursor()

    # Tabelle für erlaubte Gruppen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)

    # Tabelle für Bots (Name + Token)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            token TEXT UNIQUE
        )
    """)

    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Passwortabfrage beim Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet den Bot mit einer Passwortabfrage."""
    await update.message.reply_text("🔒 Bitte gib das Passwort ein:")

    return

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Überprüft das Passwort."""
    user_input = update.message.text.strip()
    
    if user_input == PASSWORD:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("❌ Falsches Passwort! Versuch es erneut.")

# --- Hauptmenü anzeigen ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Liste der Bots mit Buttons an."""
    cursor.execute("SELECT bot_id, name FROM bots")
    bots = cursor.fetchall()

    if not bots:
        keyboard = [[InlineKeyboardButton("➕ Bot hinzufügen", callback_data="add_bot")]]
    else:
        keyboard = [[InlineKeyboardButton(bot[1], callback_data=f"bot_{bot[0]}")] for bot in bots]
        keyboard.append([InlineKeyboardButton("➕ Bot hinzufügen", callback_data="add_bot")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 **Deine Bots:**", reply_markup=reply_markup)

# --- Bot-Details anzeigen ---
async def show_bot_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Detailansicht eines Bots mit Optionen."""
    query = update.callback_query
    bot_id = query.data.split("_")[1]

    cursor.execute("SELECT name FROM bots WHERE bot_id = ?", (bot_id,))
    bot_name = cursor.fetchone()[0]

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data=f"add_group_{bot_id}")],
        [InlineKeyboardButton("❌ Gruppe entfernen", callback_data=f"remove_group_{bot_id}")],
        [InlineKeyboardButton("⬅️ Zurück", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(f"⚙️ **Verwalte {bot_name}:**", reply_markup=reply_markup)

# --- Zurück zum Hauptmenü ---
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kehrt zum Hauptmenü zurück."""
    query = update.callback_query
    await query.message.delete()
    await show_main_menu(update, context)

# --- Callback-Handler für Inline-Buttons ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet alle Inline-Button-Interaktionen."""
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await back_to_main_menu(update, context)
    elif query.data.startswith("bot_"):
        await show_bot_details(update, context)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("🤖 Bot-Manager gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()