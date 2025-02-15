import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"  # Test-Token

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
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

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Menü für /link ---
async def link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{chat_id}")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Wähle eine Aktion:", reply_markup=reply_markup)

# --- Callback für Menü-Optionen ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("add_link_"):
        await query.message.edit_text("🔗 Sende den Link, den du zur Whitelist hinzufügen möchtest.")
        context.user_data["add_link_chat_id"] = chat_id

    elif data.startswith("show_links_"):
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()
        if not links:
            await query.message.edit_text("❌ Die Whitelist ist leer.")
            return

        keyboard = [[InlineKeyboardButton(link[0], callback_data=f"del_link_{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📋 **Whitelist:**", reply_markup=reply_markup)

    elif data.startswith("del_link_"):
        link_to_delete = data.replace("del_link_", "")
        cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link_to_delete))
        conn.commit()
        await query.answer(f"✅ Link gelöscht: {link_to_delete}")
        await query.message.edit_text("🔄 Aktualisiere das Menü mit /link.")

    elif data == "close_menu":
        await query.message.delete()

# --- Nachricht mit Link empfangen ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        if not is_whitelisted(chat_id, link):
            await context.bot.delete_message(chat_id, message.message_id)
            await context.bot.send_message(chat_id, f"🚫 {message.from_user.first_name}, dein Link wurde gelöscht.")

# --- Link zur Whitelist hinzufügen ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "add_link_chat_id" not in context.user_data:
        return

    chat_id = context.user_data.pop("add_link_chat_id")
    link = update.message.text.strip()

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Ungültiger Link. Bitte sende einen Telegram-Gruppenlink.")
        return

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()
    await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()