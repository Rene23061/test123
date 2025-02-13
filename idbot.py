import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()

    # Tabelle für die gruppenbasierte Whitelist erstellen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)

    # Tabelle für die erlaubten Gruppen erstellen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)

    conn.commit()
    print("✅ Datenbank erfolgreich initialisiert.")
    return conn, cursor

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id, cursor):
    cursor.execute("SELECT chat_id FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone() is not None

# --- Prüfen, ob ein Link in der Whitelist steht ---
def is_whitelisted(chat_id, link, cursor):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- /start-Befehl: Menü anzeigen ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔧 Verwaltung starten", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Willkommen! Wähle eine Aktion:", reply_markup=reply_markup)

# --- Menü anzeigen nach "🔧 Verwaltung starten" ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📌 Gruppen-ID anzeigen", callback_data="show_group_id")],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data="show_whitelist")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🔧 Verwaltungsmenu:", reply_markup=reply_markup)

# --- Gruppen-ID anzeigen ---
async def show_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.message.edit_text(f"📌 Die Gruppen-ID ist: `{chat_id}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_menu")]
    ]))

# --- Whitelist anzeigen ---
async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist dieser Gruppe ist leer."

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_menu")]
    ]))

# --- Zurück zum Startmenü ---
async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await start(query.message, context)

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    # Prüfen, ob die Gruppe erlaubt ist
    if not is_group_allowed(chat_id, cursor):
        return  # Gruppe ist nicht erlaubt, Bot ignoriert die Nachricht

    user = message.from_user
    user_display_name = user.username if user.username else user.full_name
    text = message.text or ""
    print(f"📩 Nachricht empfangen von {user_display_name}: {text}")

    # Nach Telegram-Gruppenlinks suchen
    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        print(f"🔗 Erkannter Telegram-Link: {link}")

        # Wenn der Link nicht in der Whitelist der aktuellen Gruppe steht, Nachricht löschen
        if not is_whitelisted(chat_id, link, cursor):
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
    application.add_handler(CommandHandler("start", start))

    # Inline-Menü Handler
    application.add_handler(CallbackQueryHandler(show_menu, pattern="^show_menu$"))
    application.add_handler(CallbackQueryHandler(show_group_id, pattern="^show_group_id$"))
    application.add_handler(CallbackQueryHandler(show_whitelist, pattern="^show_whitelist$"))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))

    # Nachrichten-Handler hinzufügen
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot wird gestartet und überwacht Telegram-Gruppenlinks...")
    application.run_polling()

if __name__ == "__main__":
    main()