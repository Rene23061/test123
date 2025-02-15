import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# --- Debugging aktivieren ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

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

# --- Prüfen, ob ein Link in der Whitelist steht ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Befehl: /id (Aktuelle Gruppen-ID anzeigen) ---
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"📌 Die Gruppen-ID ist: `{chat_id}`", parse_mode="Markdown")

# --- Befehl: /link <URL> (Link speichern) ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib einen gültigen Link an. Beispiel: /link https://t.me/gruppe")
        return

    link = context.args[0].strip()

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Kein gültiger Telegram-Link.")
        return

    logging.debug(f"📥 Speichere Link: {link} für Chat {chat_id}")

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        await update.message.reply_text(f"✅ **{link}** wurde erfolgreich zur Whitelist hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"⚠️ **{link}** ist bereits in der Whitelist.")

# --- Befehl: /del <URL> (Link löschen) ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib einen gültigen Link an. Beispiel: /del https://t.me/gruppe")
        return

    link = context.args[0].strip()
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Der Link {link} wurde erfolgreich aus der Whitelist gelöscht.")
    else:
        await update.message.reply_text(f"⚠️ Der Link {link} war nicht in der Whitelist.")

# --- Befehl: /list (Whitelist anzeigen) ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist dieser Gruppe ist leer."

    await update.message.reply_text(response, parse_mode="Markdown")

# --- Nachrichtenüberprüfung ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    user_display_name = user.username if user.username else user.full_name
    text = message.text or ""

    logging.debug(f"📩 Nachricht empfangen von {user_display_name}: {text}")

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.debug(f"🔗 Erkannter Telegram-Link: {link}")

        if not is_whitelisted(chat_id, link):
            logging.warning(f"❌ Link nicht erlaubt und wird gelöscht: {link}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 {user_display_name}, dein Link wurde automatisch gelöscht.",
                reply_to_message_id=message.message_id
            )
            await context.bot.delete_message(chat_id, message.message_id)
            return

# --- Inline-Buttons für das Menü ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Link hinzufügen", callback_data='add')],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data='list')],
        [InlineKeyboardButton("❌ Link löschen", callback_data='del')],
        [InlineKeyboardButton("🔙 Menü schließen", callback_data='close')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 **Menü auswählen:**", reply_markup=reply_markup, parse_mode="Markdown")

# --- Inline-Button Callback-Funktion ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add":
        await query.message.reply_text("📥 Sende den Link, den du hinzufügen möchtest.")
    elif query.data == "list":
        await list_links(update, context)
    elif query.data == "del":
        await query.message.reply_text("🗑 Sende den Link, den du löschen möchtest.")
    elif query.data == "close":
        await query.message.delete()

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("id", get_group_id))
    application.add_handler(CommandHandler("link", add_link))
    application.add_handler(CommandHandler("del", delete_link))
    application.add_handler(CommandHandler("list", list_links))
    application.add_handler(CommandHandler("menu", show_menu))

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, kontrolliere_nachricht))
    
    application.add_handler(CommandHandler("start", show_menu))

    application.run_polling()

if __name__ == "__main__":
    main()