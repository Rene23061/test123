import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO  # Ändere auf DEBUG, wenn detaillierte Logs gewünscht sind
)

# --- Regulärer Ausdruck für Telegram-Links ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/([+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY,
            allow_SystemCleanerBot INTEGER DEFAULT 0,
            allow_AntiGruppenlinkBot INTEGER DEFAULT 0
        )
    """)
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

# --- Prüfen, ob eine Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Prüfen, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    result = cursor.fetchone()
    logging.info(f"📋 Whitelist-Check: Gruppe={chat_id}, Link={link} → {'✅ Erlaubt' if result else '❌ Nicht erlaubt'}")
    return result is not None

# --- Prüfen, ob der Benutzer Admin/Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int):
    chat_member = await update.effective_chat.get_member(user_id)
    return chat_member.status in ["administrator", "creator"]

# --- Nachrichtenkontrolle & Link-Löschung ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not is_group_allowed(chat_id):
        return

    if not message or not message.text:
        return

    user = message.from_user
    text = message.text.strip()
    logging.info(f"📩 Nachricht von {user.full_name}: {text}")

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.info(f"🔍 Erkannter Telegram-Link: {link}")

        if not is_whitelisted(chat_id, link):
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
            return

# --- Befehl: /link (Öffnet das Menü zur Linkverwaltung) ---
async def link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt.")
        return

    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ Nur Administratoren können diesen Befehl verwenden!")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{chat_id}")]
    ]
    await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link hinzufügen ---
async def add_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]
    user_id = query.from_user.id

    if not await is_admin(update, user_id):
        await query.answer("⛔ Nur Administratoren können Links hinzufügen!", show_alert=True)
        return

    await query.message.edit_text("✏️ Bitte sende mir den **Link**, den du zur Whitelist hinzufügen möchtest.")
    context.user_data["waiting_for_link"] = chat_id

# --- Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")
    user_id = update.message.from_user.id

    if not chat_id:
        return

    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ Nur Administratoren können Links hinzufügen!")
        return

    link = update.message.text.strip()
    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("⚠️ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
        return

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")

    context.user_data.pop("waiting_for_link", None)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle & Callback-Handler
    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(CallbackQueryHandler(add_link_prompt, pattern="add_link_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    # Nachrichtenkontrolle
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()