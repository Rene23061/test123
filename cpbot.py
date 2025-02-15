import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

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

def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id if query else update.message.chat_id

    if not is_group_allowed(chat_id):
        await (query.message if query else update.message).reply_text("❌ Diese Gruppe ist nicht erlaubt.")
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Links anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("⬅️ Zurück", callback_data="back")]
    ]
    
    if query:
        await query.message.edit_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("📌 Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()
    
    text = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links) if links else "❌ Keine gespeicherten Links."

    keyboard = [[InlineKeyboardButton("⬅️ Zurück", callback_data="menu")]]
    await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def request_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("✏️ Bitte sende den Link, den du hinzufügen möchtest.")
    context.user_data["awaiting_link"] = True

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_link" not in context.user_data:
        return
    
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()

    await update.message.reply_text(f"✅ Link hinzugefügt: {link}")
    context.user_data.pop("awaiting_link")

async def request_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Keine gespeicherten Links.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück", callback_data="menu")]]))
        return

    keyboard = [[InlineKeyboardButton(link[0], callback_data=f"confirm_delete|{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="menu")])

    await query.message.edit_text("🗑 Wähle einen Link zum Löschen:", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    link = query.data.split("|")[1]
    
    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete|{link}")],
        [InlineKeyboardButton("❌ Nein, zurück", callback_data="delete_link")]
    ]
    await query.message.edit_text(f"⚠️ Soll der Link wirklich gelöscht werden?\n\n🔗 {link}", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    link = query.data.split("|")[1]
    chat_id = query.message.chat_id

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.message.edit_text(f"✅ Link gelöscht: {link}")
    await request_delete_link(update, context)

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
    elif action.startswith("confirm_delete"):
        await confirm_delete(update, context)
    elif action.startswith("delete"):
        await delete_link(update, context)
    elif action == "back":
        await query.message.delete()

def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()