import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob der Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{update.message.chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{update.message.chat_id}")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 Link-Verwaltung:", reply_markup=reply_markup)

# --- Callback für Menü-Aktionen ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data.startswith("add_link_"):
        await query.message.reply_text("Bitte sende den Link, den du hinzufügen möchtest:")
        context.user_data["awaiting_link"] = chat_id

    elif data.startswith("show_links_"):
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()
        if not links:
            await query.message.edit_text("❌ Die Whitelist ist leer.")
        else:
            keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_{link[0]}")] for link in links]
            keyboard.append([InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text("📋 Whitelist:", reply_markup=reply_markup)

    elif data.startswith("delete_"):
        link_to_delete = data.replace("delete_", "")
        cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link_to_delete))
        conn.commit()
        await query.message.reply_text(f"✅ {link_to_delete} wurde aus der Whitelist entfernt.")

    elif data == "close_menu":
        await query.message.delete()

# --- Link hinzufügen ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("awaiting_link")
    if chat_id is None:
        return

    link = update.message.text.strip()
    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()
    await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.", parse_mode="Markdown")
    del context.user_data["awaiting_link"]

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        if not is_whitelisted(chat_id, link):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Dein Link wurde automatisch gelöscht!",
                reply_to_message_id=message.message_id
            )
            await context.bot.delete_message(chat_id, message.message_id)
            return

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))
    application.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()