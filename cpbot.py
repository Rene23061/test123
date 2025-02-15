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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob eine Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT chat_id FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone() is not None

# --- Prüfen, ob ein Nutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# --- Hauptmenü öffnen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Nur Admins oder Gruppeninhaber können dieses Menü öffnen.")
        return
    if not is_group_allowed(update.effective_chat.id):
        await update.message.reply_text("🚫 Dieser Bot ist für diese Gruppe nicht aktiviert.")
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Links anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("📴 Menü schließen", callback_data="close")]
    ]
    await update.message.reply_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Callback-Handler für Menü-Buttons ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data

    if action == "show_links":
        await show_links(update, context)
    elif action == "add_link":
        await request_add_link(update, context)
    elif action == "delete_link":
        await request_delete_link(update, context)
    elif action.startswith("confirm_delete"):
        await confirm_delete(update, context)
    elif action.startswith("delete"):
        await delete_link(update, context)
    elif action == "close":
        await query.message.delete()

# --- Whitelist anzeigen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()
    text = "📋 **Whitelist dieser Gruppe:**\n\n" + "\n".join(f"- {link[0]}" for link in links) if links else "❌ Keine gespeicherten Links."
    keyboard = [[InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="menu")]]
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
    await update.message.reply_text(f"✅ Link wurde erfolgreich eingetragen: {link}")

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
    query = update.callback_query
    chat_id = query.message.chat_id
    link = query.data.split("|")[1]
    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()
    await request_delete_link(update, context)

# --- Nachrichtenkontrolle (Löschen unerlaubter Links) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        if cursor.fetchone() is None:
            try:
                await context.bot.delete_message(chat_id, message.message_id)
                await context.bot.send_message(chat_id, f"🚫 [{user.full_name}](tg://user?id={user.id}), dein Link wurde gelöscht.", parse_mode="Markdown")
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen der Nachricht: {e}")

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