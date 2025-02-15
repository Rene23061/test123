import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
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

# --- Prüfen, ob ein Nutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else update.callback_query.message.chat_id
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id

    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# --- Menü öffnen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Links anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("📴 Menü schließen", callback_data="close")]
    ]

    if update.message:
        await update.message.reply_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.edit_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Button-Handler für das Menü ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    action = query.data
    if action == "menu":
        await show_menu(update, context)
    elif action == "show_links":
        await show_links(update, context)
    elif action == "add_link":
        await request_add_link(update, context)
    elif action == "delete_link":
        await request_delete_link(update, context)
    elif action == "close":
        await query.message.delete()

# --- **Fix für den Zurück-Button in der Link-Liste** ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        text = "📋 **Whitelist dieser Gruppe:**\n\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        text = "❌ Keine gespeicherten Links."

    keyboard = [
        [InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="menu")]
    ]

    await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Link hinzufügen ---
async def request_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    context.user_data["awaiting_link"] = chat_id

    keyboard = [[InlineKeyboardButton("⬅️ Abbrechen", callback_data="menu")]]
    await update.callback_query.message.edit_text("✏️ Bitte sende den Link, den du hinzufügen möchtest.", reply_markup=InlineKeyboardMarkup(keyboard))

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if context.user_data.get("awaiting_link") != chat_id:
        return

    link = update.message.text.strip()

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()

    context.user_data.pop("awaiting_link", None)

    await request_delete_link(update, context)

# --- Link löschen ---
async def request_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await update.callback_query.message.edit_text("❌ Keine gespeicherten Links.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück", callback_data="menu")]]))
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {link[0]}", callback_data=f"confirm_delete|{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="menu")])

    await update.callback_query.message.edit_text("🗑 Wähle einen Link zum Löschen:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    link = update.callback_query.data.split("|")[1]

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await request_delete_link(update, context)

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    text = message.text or ""

    if context.user_data.get("awaiting_link") == chat_id:
        return  # Während des Eintragens keine Prüfung!

    username = f"[@{user.username}](tg://user?id={user.id})" if user.username else f"[{user.full_name}](tg://user?id={user.id})"

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        if cursor.fetchone() is None:
            try:
                await context.bot.delete_message(chat_id, message.message_id)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {username}, dein Gruppenlink wurde automatisch gelöscht.\n"
                         "Bitte frage einen Admin, falls du Links posten möchtest.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen oder Senden der Nachricht: {e}")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kontrolliere_nachricht), group=-1)
    application.run_polling()

if __name__ == "__main__":
    main()