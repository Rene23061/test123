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

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Link zur Whitelist hinzufügen ---
def add_link_to_db(chat_id, link):
    logging.debug(f"🔍 Versuche, den Link {link} für Chat {chat_id} zur Whitelist hinzuzufügen...")
    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        logging.info(f"✅ Link erfolgreich hinzugefügt: {link}")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"⚠️ Link bereits in der Whitelist: {link}")
        return False  # Link existiert bereits

# --- Link speichern, wenn Nutzer ihn sendet ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    logging.debug(f"📥 Erhaltener Link: {link} für Chat {chat_id}")

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Dies ist kein gültiger Telegram-Link.")
        logging.warning(f"❌ Ungültiger Link erkannt: {link}")
        return

    if add_link_to_db(chat_id, link):
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
    else:
        await update.message.reply_text(f"⚠️ **{link}** ist bereits in der Whitelist.")

    # **Nach erfolgreicher Speicherung die Löschung unterdrücken**
    context.user_data["awaiting_link"] = None
    logging.debug("🟢 Link erfolgreich gespeichert, Filter deaktiviert.")

# --- Liste aller Links anzeigen ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    logging.debug(f"📋 Rufe Whitelist für Chat {chat_id} ab...")

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist dieser Gruppe ist leer."

    logging.debug(f"🔍 Abgerufene Links: {links}")

    await update.message.reply_text(response, parse_mode="Markdown")

# --- Nachrichten prüfen und ggf. löschen ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text

    # **Prüfen, ob wir gerade einen Link eintragen**
    if context.user_data.get("awaiting_link") == chat_id:
        logging.debug(f"⚠️ Nachricht wird ignoriert, da Link zur Whitelist hinzugefügt wird: {text}")
        return

    logging.debug(f"📩 Nachricht erhalten: {text}")

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.debug(f"🔗 Erkannter Telegram-Link: {link}")

        if not is_whitelisted(chat_id, link):
            logging.info(f"❌ Link nicht erlaubt, wird gelöscht: {link}")
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
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data="show_links")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text("📌 Wähle eine Option:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📌 Wähle eine Option:", reply_markup=reply_markup)

# --- Callback-Funktion für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "add_link":
        await query.message.edit_text("Sende mir bitte den Link, den du zur Whitelist hinzufügen möchtest.")
        context.user_data["awaiting_link"] = chat_id
        logging.debug(f"🟡 Warte auf einen Link für Chat {chat_id}...")

    elif query.data == "show_links":
        await list_links(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CommandHandler("list", list_links))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), kontrolliere_nachricht))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    logging.info("🚀 Bot gestartet! Warte auf Nachrichten...")
    application.run_polling()

if __name__ == "__main__":
    main()