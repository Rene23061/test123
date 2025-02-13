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
    await update.message.reply_text("🔒 Bitte gib das Passwort ein:")

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == PASSWORD:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("❌ Falsches Passwort! Versuch es erneut.")

# --- Hauptmenü anzeigen ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await query.message.edit_text("✍️ Bitte sende mir den Namen des neuen Bots.")

    # Speichert den Status, dass wir auf den Bot-Namen warten
    context.user_data["waiting_for_bot_name"] = True

# --- Funktion zum Speichern des Bots nach Namenseingabe ---
async def save_bot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for_bot_name" in context.user_data and context.user_data["waiting_for_bot_name"]:
        bot_name = update.message.text.strip()
        await update.message.reply_text("✍️ Jetzt bitte das Bot-Token senden.")

        # Speichert den Namen für den nächsten Schritt
        context.user_data["new_bot_name"] = bot_name
        context.user_data["waiting_for_bot_name"] = False
        context.user_data["waiting_for_bot_token"] = True

# --- Funktion zum Speichern des Bot-Tokens in die Datenbank ---
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

# --- Bot-Details anzeigen ---
async def show_bot_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_id = query.data.split("_")[1]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM bots WHERE bot_id = ?", (bot_id,))
    bot_name = cursor.fetchone()[0]
    conn.close()

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data=f"add_group_{bot_id}")],
        [InlineKeyboardButton("❌ Gruppe entfernen", callback_data=f"remove_group_{bot_id}")],
        [InlineKeyboardButton("⬅️ Zurück", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(f"⚙️ **Verwalte {bot_name}:**", reply_markup=reply_markup)

# --- Zurück zum Hauptmenü ---
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()
    await show_main_menu(update, context)

# --- Callback-Handler für Inline-Buttons ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await back_to_main_menu(update, context)
    elif query.data == "add_bot":
        await add_bot(update, context)
    elif query.data.startswith("bot_"):
        await show_bot_details(update, context)

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