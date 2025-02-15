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
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Hauptmenü ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Links anzeigen", callback_data="open_show_links")],
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="open_add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="open_delete_link")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 **Hauptmenü**\nWähle ein Menü:", reply_markup=reply_markup, parse_mode="Markdown")

# --- Menü: Links anzeigen ---
async def show_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        response = "📋 **Whitelist dieser Gruppe:**\n" + "\n".join(f"- {link[0]}" for link in links)
    else:
        response = "❌ Die Whitelist ist leer."

    keyboard = [
        [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")],
        [InlineKeyboardButton("❌ Schließen", callback_data="close_menu")]
    ]
    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Menü: Link hinzufügen ---
async def add_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("ℹ️ **Sende jetzt den neuen Link als Nachricht.**\n🔙 Drücke /cancel zum Abbrechen.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")],
        [InlineKeyboardButton("❌ Schließen", callback_data="close_menu")]
    ]))
    context.user_data["awaiting_link"] = True  # Wartet auf Link

# --- Link hinzufügen (Speicherung) ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    link = update.message.text.strip()

    if not context.user_data.get("awaiting_link"):
        return  # Ignorieren, falls kein Link erwartet wird

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("❌ Ungültiger Link. Bitte sende einen gültigen Telegram-Link.")
        return

    cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
    conn.commit()

    await update.message.reply_text(f"✅ Link gespeichert:\n🔗 {link}")
    context.user_data["awaiting_link"] = False  # Wartezustand deaktivieren

# --- Menü: Link löschen ---
async def delete_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.edit_message_text("❌ Keine Links zum Löschen.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")],
            [InlineKeyboardButton("❌ Schließen", callback_data="close_menu")]
        ]))
        return

    keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_confirm|{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])
    keyboard.append([InlineKeyboardButton("❌ Schließen", callback_data="close_menu")])
    await query.edit_message_text("❌ **Wähle einen Link zum Löschen:**", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Link löschen bestätigen ---
async def confirm_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    link = query.data.split("|")[1]
    await query.answer()

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()
    await query.edit_message_text(f"✅ Link gelöscht: {link}", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="delete_link")],
        [InlineKeyboardButton("❌ Schließen", callback_data="close_menu")]
    ]))

# --- Menü schließen ---
async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Menü geschlossen.")

# --- Nachrichtenkontrolle (Links löschen) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text or ""

    if context.user_data.get("awaiting_link"):
        return  # Keine Link-Prüfung im Hinzufügen-Menü

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
        result = cursor.fetchone()

        if result:
            return  # Link ist erlaubt

        await context.bot.send_message(chat_id, text=f"🚫 Dein Link wurde gelöscht!", reply_to_message_id=message.message_id)
        await context.bot.delete_message(chat_id, message.message_id)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", show_main_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_link))

    application.add_handler(CallbackQueryHandler(show_links_menu, pattern="^open_show_links$"))
    application.add_handler(CallbackQueryHandler(add_link_menu, pattern="^open_add_link$"))
    application.add_handler(CallbackQueryHandler(delete_link_menu, pattern="^open_delete_link$"))
    application.add_handler(CallbackQueryHandler(confirm_delete_link, pattern="^delete_confirm\\|"))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(close_menu, pattern="^close_menu$"))

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()