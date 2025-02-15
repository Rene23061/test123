import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
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

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Überprüfung, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Befehl: /id (Gruppen-ID anzeigen) ---
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"📌 Die Gruppen-ID ist: `{chat_id}`", parse_mode="Markdown")

# --- Befehl: /link <URL> (Link zur Whitelist hinzufügen mit Inline-Button) ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib einen gültigen Link an. Beispiel: /link https://t.me/gruppe")
        return

    link = context.args[0].strip()

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Schließen", callback_data="close_message")]
        ])

        await update.message.reply_text(
            f"✅ Der Link {link} wurde erfolgreich zur Whitelist hinzugefügt.",
            reply_markup=keyboard
        )

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Der Link ist bereits in der Whitelist der Gruppe.")

# --- Callback-Handler zum Schließen der Nachricht ---
async def close_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.message.delete()
    await query.answer()

# --- Befehl: /del <URL> (Link aus der Whitelist löschen) ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Bitte gib einen gültigen Link an. Beispiel: /del https://t.me/gruppe")
        return

    link = context.args[0].strip()
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Der Link {link} wurde erfolgreich aus der Whitelist der Gruppe gelöscht.")
    else:
        await update.message.reply_text(f"⚠️ Der Link {link} war nicht in der Whitelist der Gruppe.")

# --- Befehl: /list (Whitelist anzeigen) ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist dieser Gruppe ist leer."

    await update.message.reply_text(response, parse_mode="Markdown")

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not is_group_allowed(chat_id):
        print(f"⛔ Gruppe {chat_id} ist nicht erlaubt. Nachricht wird ignoriert.")
        return

    user = message.from_user
    user_display_name = user.username if user.username else user.full_name
    text = message.text or ""
    print(f"📩 Nachricht empfangen von {user_display_name}: {text}")

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        print(f"🔗 Erkannter Telegram-Link: {link}")

        if not is_whitelisted(chat_id, link):
            print(f"❌ Link nicht erlaubt und wird gelöscht: {link}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Hallo {user_display_name}, dein Link wurde automatisch gelöscht. "
                     f"Bitte kontaktiere einen Admin, wenn du Fragen hast.",
                reply_to_message_id=message.message_id
            )
            await context.bot.delete_message(chat_id, message.message_id)
            return

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle hinzufügen
    application.add_handler(CommandHandler("id", get_group_id))
    application.add_handler(CommandHandler("link", add_link))
    application.add_handler(CommandHandler("del", delete_link))
    application.add_handler(CommandHandler("list", list_links))

    # Callback-Handler für Inline-Buttons
    application.add_handler(CallbackQueryHandler(close_message, pattern="close_message"))

    # Nachrichten-Handler hinzufügen
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Anti-Gruppenlink-Bot gestartet und überwacht Telegram-Gruppenlinks...")
    application.run_polling()

if __name__ == "__main__":
    main()