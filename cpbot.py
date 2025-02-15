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

# --- Prüfen, ob die Gruppe für den Anti-Gruppenlink-Bot erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Befehl: /id (Aktuelle Gruppen-ID anzeigen) ---
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"📌 Die Gruppen-ID ist: `{chat_id}`", parse_mode="Markdown")

# --- Interaktive Link-Verwaltung ---
async def manage_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data=f"show_list_{chat_id}")]
    ]

    await update.message.reply_text(
        "🔗 **Link-Verwaltung:**\nWähle eine Option aus:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- Whitelist anzeigen ---
async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        new_text = "❌ Die Whitelist dieser Gruppe ist leer."
    else:
        new_text = "📋 **Whitelist:**\n" + "\n".join(f"- {link[0]}" for link in links)

    keyboard = [[InlineKeyboardButton("❌ Entfernen", callback_data=f"delete_menu_{chat_id}")]] if links else []

    if query.message.text != new_text:
        await query.message.edit_text(new_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link-Löschmenü ---
async def delete_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        new_text = "❌ Die Whitelist ist leer."
        keyboard = []
    else:
        new_text = "🗑 **Wähle einen Link zum Löschen:**"
        keyboard = [[InlineKeyboardButton(f"❌ {link[0]}", callback_data=f"delete_{chat_id}_{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"show_list_{chat_id}")])

    if query.message.text != new_text:
        await query.message.edit_text(new_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = data[1]
    link = "_".join(data[2:])

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.answer(f"✅ {link} wurde gelöscht.", show_alert=True)
    await delete_link_menu(update, context)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("id", get_group_id))
    application.add_handler(CommandHandler("link", manage_links))
    application.add_handler(CallbackQueryHandler(show_whitelist, pattern="show_list_"))
    application.add_handler(CallbackQueryHandler(delete_link_menu, pattern="delete_menu_"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="delete_"))

    print("🤖 Anti-Gruppenlink-Bot gestartet und überwacht Telegram-Gruppenlinks...")
    application.run_polling()

if __name__ == "__main__":
    main()