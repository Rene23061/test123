import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank ---
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            link TEXT NOT NULL UNIQUE
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

# --- Link zur Whitelist hinzufügen ---
def add_link_to_db(chat_id, link):
    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Link existiert bereits

# --- Link aus der Whitelist entfernen ---
def remove_link_from_db(chat_id, link):
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()
    return cursor.rowcount > 0

# --- Alle Links einer Gruppe abrufen ---
def get_links_from_db(chat_id):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    return [row[0] for row in cursor.fetchall()]

# --- Hauptmenü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data="show_links")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Wähle eine Option:", reply_markup=reply_markup)

# --- Callback-Funktion für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "add_link":
        await query.message.edit_text("Sende mir bitte den Link, den du zur Whitelist hinzufügen möchtest.")
        context.user_data["awaiting_link"] = chat_id  # Warte auf Link von diesem Chat

    elif query.data == "show_links":
        links = get_links_from_db(chat_id)
        if not links:
            await query.message.edit_text("❌ Die Whitelist ist leer.")
        else:
            keyboard = [[InlineKeyboardButton(f"❌ {link}", callback_data=f"delete_{link}")] for link in links]
            keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(f"✅ Whitelist:\n" + "\n".join(links), reply_markup=reply_markup)

    elif query.data.startswith("delete_"):
        link_to_delete = query.data.replace("delete_", "")
        if remove_link_from_db(chat_id, link_to_delete):
            await query.message.edit_text(f"✅ Der Link wurde entfernt: {link_to_delete}")
        else:
            await query.message.edit_text("⚠️ Link nicht gefunden.")

    elif query.data == "back":
        await show_menu(update, context)  # Hauptmenü erneut anzeigen

    elif query.data == "close_menu":
        await query.message.delete()

# --- Nachricht prüfen und ggf. löschen ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not is_group_allowed(chat_id):
        return  # Gruppe nicht erlaubt, Bot ignoriert Nachrichten

    if message.entities:
        for entity in message.entities:
            if entity.type == "url":
                link = message.text[entity.offset: entity.offset + entity.length]
                if not is_whitelisted(chat_id, link):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚫 Dieser Link ist nicht erlaubt und wurde entfernt: {link}"
                    )
                    await message.delete()
                    return

# --- Link speichern, wenn Nutzer ihn sendet ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_link" in context.user_data:
        chat_id = context.user_data["awaiting_link"]
        link = update.message.text

        if add_link_to_db(chat_id, link):
            await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
        else:
            await update.message.reply_text(f"⚠️ **{link}** ist bereits in der Whitelist.")

        del context.user_data["awaiting_link"]

# --- Bot starten ---
def main():
    init_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), kontrolliere_nachricht))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    application.run_polling()

if __name__ == "__main__":
    main()