import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor.execute("SELECT allow_AntiGruppenlinkBot FROM allowed_groups WHERE chat_id = ? AND allow_AntiGruppenlinkBot = 1", (chat_id,))
    return cursor.fetchone() is not None

# --- Prüfen, ob ein Benutzer Admin oder Mitglied ist ---
async def is_admin_or_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user = update.message.from_user
    member = await chat.get_member(user.id)

    return member.status in ["administrator", "creator", "member"]

# --- Hauptmenü ---
async def show_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    if not await is_admin_or_member(update, context):
        await update.message.reply_text("🚫 Du hast keine Berechtigung, dieses Menü zu öffnen.")
        return

    keyboard = [
        [InlineKeyboardButton("🔗 Link anzeigen", callback_data="show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="delete_link")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 **Linkverwaltung**\nWähle eine Option:", reply_markup=reply_markup, parse_mode="Markdown")

# --- Callback für Menü-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id

    await query.answer()

    if query.data == "show_links":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()

        if links:
            response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
        else:
            response = "❌ Die Whitelist dieser Gruppe ist leer."

        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(response, parse_mode="Markdown", reply_markup=reply_markup)

    elif query.data == "delete_link":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()

        if not links:
            await query.edit_message_text("❌ Keine Links zum Löschen vorhanden.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")]
            ]))
            return

        keyboard = [[InlineKeyboardButton(link[0], callback_data=f"confirm_delete|{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Wähle einen Link zum Löschen:", reply_markup=reply_markup)

    elif query.data.startswith("confirm_delete"):
        link = query.data.split("|")[1]
        keyboard = [
            [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_confirmed|{link}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="delete_link")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"⚠️ **Bist du sicher, dass du diesen Link löschen möchtest?**\n\n🔗 {link}", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("delete_confirmed"):
        link = query.data.split("|")[1]
        cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        conn.commit()
        await query.edit_message_text(f"✅ **Der Link wurde gelöscht:** {link}", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Zurück", callback_data="delete_link")]
        ]), parse_mode="Markdown")

    elif query.data == "main_menu":
        await show_link_menu(update, context)

    elif query.data == "close_menu":
        await query.edit_message_text("✅ Menü geschlossen.")

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not is_group_allowed(chat_id):
        return

    user = message.from_user
    user_display_name = user.username if user.username else user.full_name
    text = message.text or ""

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        if cursor.fetchone() is None:
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
    application.run_polling()

if __name__ == "__main__":
    main()