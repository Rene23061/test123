import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG
)

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            link TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Link zur Whitelist hinzufügen ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Kein gültiger Telegram-Link.")
        return

    logging.debug(f"📥 Speichere Link: {link} für Chat {chat_id}")

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"⚠️ **{link}** ist bereits in der Whitelist.")

    # Flag setzen, damit der Link nicht gelöscht wird
    context.user_data["awaiting_link"] = None

# --- Liste aller Links anzeigen ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist ist leer."

    await update.message.reply_text(response, parse_mode="Markdown")

# --- Link aus Whitelist löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = context.args[0].strip() if context.args else None

    if not link:
        await update.message.reply_text("❌ Bitte gib einen Link an, den du löschen möchtest.")
        return

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ **{link}** wurde aus der Whitelist entfernt.")
    else:
        await update.message.reply_text(f"⚠️ **{link}** war nicht in der Whitelist.")

# --- Nachrichten prüfen und ggf. löschen ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text

    # Wenn ein Link gerade gespeichert wird, ignorieren
    if context.user_data.get("awaiting_link") == chat_id:
        logging.debug(f"⚠️ Nachricht wird ignoriert, da ein Link gespeichert wird: {text}")
        return

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))

        if cursor.fetchone() is None:
            logging.info(f"❌ Unerlaubter Link, wird gelöscht: {link}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Dieser Link ist nicht erlaubt und wurde entfernt: {link}"
            )
            await message.delete()
            return

# --- Hauptmenü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id if query else update.message.chat_id

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("📋 Link anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("🗑 Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.message.edit_text("📌 Wähle eine Option:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📌 Wähle eine Option:", reply_markup=reply_markup)

# --- Callback-Funktion für Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "add_link":
        await query.message.edit_text("Sende mir bitte den Link, den du hinzufügen möchtest.")
        context.user_data["awaiting_link"] = chat_id  # Speichert den Zustand

    elif query.data == "show_links":
        await list_links(update, context)

    elif query.data == "delete_link":
        await query.message.edit_text("Nutze den Befehl: `/del <URL>` um einen Link zu löschen.", parse_mode="Markdown")

    elif query.data == "close_menu":
        await query.message.delete()

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", show_menu))
    application.add_handler(CommandHandler("list", list_links))
    application.add_handler(CommandHandler("del", delete_link))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nur Links prüfen, nicht gesamte Nachrichten
    application.add_handler(MessageHandler(filters.Entity("url"), kontrolliere_nachricht))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))

    logging.info("🚀 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()