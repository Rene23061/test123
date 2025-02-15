import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

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
            link TEXT UNIQUE
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Link in der Whitelist steht ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Inline-Menü erstellen ---
def get_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("❌ Link löschen", callback_data="del_link")],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data="list_links")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Menü anzeigen oder aktualisieren ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=get_menu(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text("🔗 **Link-Verwaltung:**", reply_markup=get_menu(), parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "add_link":
        context.user_data["action"] = "add_link"
        await query.message.edit_text("📩 Bitte sende den Link, den du hinzufügen möchtest:", reply_markup=get_menu())

    elif query.data == "del_link":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()

        if not links:
            await query.message.edit_text("❌ Keine Links in der Whitelist.", reply_markup=get_menu(), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(link[0], callback_data=f"confirm_del_{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text("🗑 **Wähle einen Link zum Löschen:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        link_to_delete = query.data.replace("confirm_del_", "")
        keyboard = [
            [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_{link_to_delete}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="del_link")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"⚠️ Bist du sicher, dass du diesen Link löschen möchtest?\n\n🔗 {link_to_delete}",
                                      reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        link_to_delete = query.data.replace("delete_", "")
        cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link_to_delete))
        conn.commit()

        if cursor.rowcount > 0:
            await query.message.edit_text(f"✅ Link gelöscht: {link_to_delete}", reply_markup=get_menu(), parse_mode="Markdown")
        else:
            await query.message.edit_text("⚠️ Link war nicht in der Whitelist.", reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "list_links":
        cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
        links = cursor.fetchall()
        if links:
            response = "📋 **Whitelist:**\n" + "\n".join(f"- {link[0]}" for link in links)
        else:
            response = "❌ Die Whitelist ist leer."
        await query.message.edit_text(response, reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Nachrichten-Handler für Link-Aktionen ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_link":
            if TELEGRAM_LINK_PATTERN.match(text):
                try:
                    cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, text))
                    conn.commit()
                    await update.message.reply_text(f"✅ Link hinzugefügt: {text}")
                except sqlite3.IntegrityError:
                    await update.message.reply_text("⚠️ Link ist bereits in der Whitelist.")
            else:
                await update.message.reply_text("❌ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
            return await show_menu(update, context)

    # Falls kein Befehl aktiv ist, Link überprüfen
    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        if not is_whitelisted(chat_id, link):
            await update.message.reply_text(f"🚫 Link nicht erlaubt: {link}")
            await context.bot.delete_message(chat_id, update.message.message_id)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("menu", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler für Links
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()