import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

# --- Regex für Topic-ID aus Gruppenlink ---
TOPIC_ID_PATTERN = re.compile(r"https://t\.me/c/\d+/(\d+)")

# --- Verbindung zur SQLite-Datenbank ---
def init_db():
    conn = sqlite3.connect("topics.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            chat_id INTEGER,
            topic_id INTEGER
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Thema gesperrt ist ---
def is_topic_restricted(chat_id, topic_id):
    cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
    return cursor.fetchone() is not None

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Thema sperren", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entsperren", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    if update.message:
        await update.message.reply_text("🔒 **Themen-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text("🔒 **Themen-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Thema-ID** oder den **Gruppenlink**:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gesperrten Themen vorhanden.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(str(topic[0]), callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        await query.message.edit_text("🗑 **Wähle ein Thema zum Entsperren:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_id = query.data.replace("confirm_del_", "")
        keyboard = [
            [InlineKeyboardButton("✅ Ja, entsperren", callback_data=f"delete_{topic_id}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="del_topic")]
        ]
        await query.message.edit_text(f"⚠️ **Thema {topic_id} wirklich entsperren?**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        topic_id = query.data.replace("delete_", "")
        cursor.execute("DELETE FROM topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()

        if cursor.rowcount > 0:
            await query.message.edit_text(f"✅ Thema entsperrt: {topic_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")
        else:
            await query.message.edit_text("⚠️ Thema war nicht gesperrt.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        if topics:
            response = "📋 **Gesperrte Themen:**\n" + "\n".join(f"- {topic[0]}" for topic in topics)
        else:
            response = "❌ Keine gesperrten Themen."
        await query.message.edit_text(response, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Nachrichten-Handler für Thema-Einträge ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            match = TOPIC_ID_PATTERN.match(text)
            topic_id = match.group(1) if match else text

            if topic_id.isdigit():
                cursor.execute("INSERT INTO topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema gesperrt: {topic_id}")
            else:
                await update.message.reply_text("❌ Ungültige ID! Bitte sende eine **gültige Thema-ID oder einen Gruppenlink.**")
            return await show_menu(update, context)

    # Falls eine gesperrte Topic-ID erkannt wird, Nachricht löschen
    cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ?", (chat_id,))
    restricted_topics = [str(row[0]) for row in cursor.fetchall()]

    if update.message.message_thread_id and str(update.message.message_thread_id) in restricted_topics:
        await context.bot.delete_message(chat_id, update.message.message_id)
        await update.message.reply_text("🚫 Nachricht gelöscht: Thema ist gesperrt.")

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("noread", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler für Themen-Einträge
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()