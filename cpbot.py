import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT UNIQUE
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- /del: Zeigt gespeicherte Links mit Löschoption ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("❌ Schließen", callback_data="close")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Wähle einen Link zum Löschen:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Es gibt keine gespeicherten Links.")

# --- Callback: Bestätigung zum Löschen ---
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    link = query.data.replace("delete_", "", 1)

    logger.info(f"Link zur Löschung ausgewählt: {link}")

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"confirm_delete_{link}")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(f"Bist du sicher, dass du den Link löschen möchtest?\n{link}", reply_markup=reply_markup)

# --- Callback: Link endgültig löschen ---
async def delete_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    link = query.data.replace("confirm_delete_", "", 1)
    chat_id = query.message.chat.id

    logger.info(f"Versuche, Link zu löschen: {link} für Chat-ID: {chat_id}")

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        logger.info(f"Erfolgreich gelöscht: {link}")
        keyboard = [
            [InlineKeyboardButton("🗑 Weiteren Link löschen", callback_data="del")],
            [InlineKeyboardButton("❌ Schließen", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(f"✅ Gelöscht: {link}", reply_markup=reply_markup)
    else:
        logger.warning(f"Link nicht in der Datenbank gefunden: {link}")
        await query.message.reply_text(f"⚠️ Link nicht gefunden: {link}")

# --- Callback: Menü schließen ---
async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("del", delete_link))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(delete_confirmed, pattern="^confirm_delete_"))
    application.add_handler(CallbackQueryHandler(close, pattern="^close$"))

    logger.info("🤖 Bot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()