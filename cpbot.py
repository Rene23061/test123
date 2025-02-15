import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Logging aktivieren ---
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Telegram-Bot-Token ---
TOKEN = "DEIN_TELEGRAM_BOT_TOKEN"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/([+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank ---
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

# --- Prüfen, ob ein Link in der Whitelist ist ---
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
    
    await update.message.reply_text("🔗 **Link-Verwaltung**\nWähle eine Option:", 
                                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Callback für Menü-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    chat_id = int(data.split("_")[-1])

    if data.startswith("add_link_"):
        context.user_data["waiting_for_link"] = chat_id
        await query.message.edit_text("✏ Bitte sende den Link, den du hinzufügen möchtest.")

    elif data.startswith("show_links_"):
        await show_links(update, context, chat_id)

    elif data.startswith("delete_link_"):
        link = data.replace("delete_link_", "")
        await delete_link(update, context, chat_id, link)

    elif data == "close_menu":
        await query.message.delete()

# --- Link anzeigen/löschen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    query = update.callback_query

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Die Whitelist ist leer.")
        return

    keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_link_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")])

    await query.message.edit_text("📋 **Whitelist:**\n🔽 Wähle einen Link zum Löschen:", 
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id, link):
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await update.callback_query.message.edit_text(f"✅ **{link}** wurde aus der Whitelist gelöscht.")

# --- Nachrichtenkontrolle (Löschen unerlaubter Links) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not message or not message.text:
        return

    user = message.from_user
    text = message.text.strip()

    # Falls der Bot auf einen Link-Eintrag wartet, soll er diese Nachricht ignorieren
    if context.user_data.get("waiting_for_link") == chat_id:
        logging.info(f"✋ Nachricht NICHT gelöscht – Bot wartet auf Link-Eingabe in {chat_id}")
        return

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.info(f"🔗 Erkannter Link: {link}")

        if is_whitelisted(chat_id, link):
            logging.info(f"✅ Link ist in der Whitelist. Nachricht bleibt bestehen.")
        else:
            logging.warning(f"🚨 Unerlaubter Link erkannt! Lösche Nachricht von {user.full_name}: {link}")
            try:
                await message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {user.full_name}, dein Link wurde gelöscht!\n❌ Nicht erlaubter Link: {link}",
                    reply_to_message_id=message.message_id
                )
            except Exception as e:
                logging.error(f"⚠️ Fehler beim Löschen der Nachricht: {e}")

# --- Link hinzufügen ---
async def handle_new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")
    if not chat_id:
        return

    message = update.message
    text = message.text.strip()

    if TELEGRAM_LINK_PATTERN.match(text):
        try:
            cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, text))
            conn.commit()
            await message.reply_text(f"✅ **{text}** wurde zur Whitelist hinzugefügt.")
        except sqlite3.IntegrityError:
            await message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")
    else:
        await message.reply_text("❌ Ungültiger Link. Bitte versuche es erneut.")

    context.user_data["waiting_for_link"] = None  # Zurücksetzen

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("link", link_menu))

    # Callbacks für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))
    application.add_handler(MessageHandler(filters.TEXT, handle_new_link))

    logging.info("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()