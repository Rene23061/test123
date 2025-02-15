import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging für Debugging ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def debug_log(message):
    logging.info(message)

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

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

# --- Status für ConversationHandler ---
AWAITING_LINK = 1

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Prüfen, ob ein Benutzer Admin oder Mitglied ist ---
async def is_admin_or_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    return member.status in ["administrator", "creator", "member"]

# --- Hauptmenü ---
async def show_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    debug_log(f"🔹 Hauptmenü aufgerufen für Chat {chat_id}")

    if not is_group_allowed(chat_id):
        await context.bot.send_message(chat_id, "❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    if not await is_admin_or_member(update, context):
        await context.bot.send_message(chat_id, "🚫 Du hast keine Berechtigung, dieses Menü zu öffnen.")
        return

    keyboard = [
        [InlineKeyboardButton("🔗 Link anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id, "📋 **Linkverwaltung**\nWähle eine Option:", reply_markup=reply_markup, parse_mode="Markdown")

# --- Callback für Menü-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    await query.answer()
    debug_log(f"🔹 Callback erhalten: {query.data} in Chat {chat_id}")

    if query.data == "show_links":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links) if links else "❌ Die Whitelist dieser Gruppe ist leer."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")]]
        await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_link":
        debug_log(f"🔹 Link hinzufügen gestartet für Chat {chat_id}")
        await query.edit_message_text("ℹ️ Bitte sende den neuen Link als Nachricht.")
        return AWAITING_LINK

    elif query.data == "main_menu":
        await show_link_menu(update, context)

    elif query.data == "close_menu":
        await query.edit_message_text("✅ Menü geschlossen.")

# --- Link zur Whitelist hinzufügen ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    link = update.message.text.strip()

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Das ist kein gültiger Telegram-Link. Bitte sende einen gültigen Link.")
        return

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()
    
    # Überprüfen, ob der Link erfolgreich gespeichert wurde
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    result = cursor.fetchone()
    
    if result:
        debug_log(f"✅ Link hinzugefügt: {link} für Chat {chat_id}")
        await update.message.reply_text(f"✅ Der Link wurde erfolgreich hinzugefügt:\n🔗 {link}")
    else:
        debug_log(f"⚠️ Fehler: Link konnte nicht gespeichert werden: {link}")
        await update.message.reply_text("⚠️ Fehler beim Speichern des Links. Bitte versuche es erneut.")

    await show_link_menu(update, context)
    return ConversationHandler.END

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text or ""

    if not is_group_allowed(chat_id):
        return

    user = message.from_user
    user_display_name = user.username if user.username else user.full_name

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        # **Whitelist prüfen, bevor gelöscht wird**
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        if cursor.fetchone():
            debug_log(f"✅ Erlaubter Link erkannt: {link} von {user_display_name}")
            return  # Link ist erlaubt, keine Aktion

        debug_log(f"🚫 Nicht erlaubter Link entdeckt & gelöscht: {link} von {user_display_name}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 Hallo {user_display_name}, dein Link wurde automatisch gelöscht.",
            reply_to_message_id=message.message_id
        )
        await context.bot.delete_message(chat_id, message.message_id)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_link_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot gestartet...")
    debug_log("🤖 Bot wurde erfolgreich gestartet.")
    application.run_polling()

if __name__ == "__main__":
    main()