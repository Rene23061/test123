import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
            link TEXT UNIQUE
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Link in der Whitelist steht ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Inline-Menü für Link-Verwaltung ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="del_link")],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data="list_links")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id

    if query.data == "add_link":
        await query.message.reply_text("Bitte sende den Link, den du hinzufügen möchtest:")
        context.user_data["action"] = "add_link"
    
    elif query.data == "del_link":
        await query.message.reply_text("Bitte sende den Link, den du löschen möchtest:")
        context.user_data["action"] = "del_link"
    
    elif query.data == "list_links":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()
        if links:
            response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
        else:
            response = "❌ Die Whitelist dieser Gruppe ist leer."
        await query.message.reply_text(response, parse_mode="Markdown")

    elif query.data == "close_menu":
        await query.message.delete()

# --- Link hinzufügen ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    if TELEGRAM_LINK_PATTERN.match(link):
        try:
            cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
            conn.commit()
            await update.message.reply_text(f"✅ Der Link wurde erfolgreich hinzugefügt: {link}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")
    else:
        await update.message.reply_text("❌ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Der Link wurde gelöscht: {link}")
    else:
        await update.message.reply_text("⚠️ Der Link war nicht in der Whitelist.")

# --- Nachrichtenprüfung und Link-Filter ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        if not is_whitelisted(chat_id, link):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Dieser Link ist nicht erlaubt und wurde entfernt: {link}",
                reply_to_message_id=message.message_id
            )
            await context.bot.delete_message(chat_id, message.message_id)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("menu", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichtenhandler für Links
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()