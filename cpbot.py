import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank ---
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

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Sichere Methode zur Ermittlung von chat_id ---
def get_chat_id(update: Update):
    if update.message:
        return update.message.chat_id
    elif update.callback_query:
        return update.callback_query.message.chat_id
    return None

# --- Menü öffnen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt.") if update.message else await update.callback_query.message.edit_text("❌ Diese Gruppe ist nicht erlaubt.")
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Links anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
    ]
    
    if update.message:
        await update.message.reply_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.edit_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Links anzeigen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()
    
    text = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links) if links else "❌ Keine gespeicherten Links."

    keyboard = [[InlineKeyboardButton("⬅️ Zurück", callback_data="menu")]]
    await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Link hinzufügen ---
async def request_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text("✏️ Bitte sende den Link, den du hinzufügen möchtest.")
    context.user_data["awaiting_link"] = True

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_link" not in context.user_data:
        return
    
    chat_id = get_chat_id(update)
    if chat_id is None:
        return

    link = update.message.text.strip()

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()

    await update.message.reply_text(f"✅ Link hinzugefügt: {link}")
    context.user_data.pop("awaiting_link")

# --- Link löschen ---
async def request_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await update.callback_query.message.edit_text("❌ Keine gespeicherten Links.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück", callback_data="menu")]]))
        return

    keyboard = [[InlineKeyboardButton(link[0], callback_data=f"confirm_delete|{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="menu")])

    await update.callback_query.message.edit_text("🗑 Wähle einen Link zum Löschen:", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.callback_query.data.split("|")[1]
    
    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete|{link}")],
        [InlineKeyboardButton("❌ Nein, zurück", callback_data="delete_link")]
    ]
    await update.callback_query.message.edit_text(f"⚠️ Soll der Link wirklich gelöscht werden?\n\n🔗 {link}", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return

    link = update.callback_query.data.split("|")[1]

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await update.callback_query.message.edit_text(f"✅ Link gelöscht: {link}")
    await request_delete_link(update, context)

# --- Button-Handler für das Menü ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.callback_query.data

    if action == "menu":
        await show_menu(update, context)
    elif action == "show_links":
        await show_links(update, context)
    elif action == "add_link":
        await request_add_link(update, context)
    elif action == "delete_link":
        await request_delete_link(update, context)
    elif action.startswith("confirm_delete"):
        await confirm_delete(update, context)
    elif action.startswith("delete"):
        await delete_link(update, context)

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    if chat_id is None:
        return  

    message = update.message
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        link_in_whitelist = cursor.fetchone()

        if link_in_whitelist is None:
            await context.bot.delete_message(chat_id, message.message_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Link von {message.from_user.full_name} wurde gelöscht.",
                reply_to_message_id=message.message_id
            )

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot gestartet und überwacht Telegram-Links!")
    application.run_polling()

if __name__ == "__main__":
    main()