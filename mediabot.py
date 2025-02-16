import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# 🔹 Test-Bot-Token
TOKEN = "8069716549:AAGfRNlsOIOlsMBZrAcsiB_IjV5yz3XOM8A"

# 🔹 Verbindung zur SQLite-Datenbank herstellen
def init_db():
    conn = sqlite3.connect("mediabot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_topics (
            chat_id INTEGER, 
            topic_id INTEGER, 
            PRIMARY KEY (chat_id, topic_id)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# 🔹 Prüfen, ob ein Thema eingeschränkt ist
def is_topic_restricted(chat_id, topic_id):
    cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
    return cursor.fetchone() is not None

# 🔹 Admin-Berechtigung prüfen
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

# 🔹 Inline-Menü anzeigen
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Nur Admins können dieses Menü nutzen!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Thema hinzufügen", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entfernen", callback_data="remove_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🔒 **Themen-Verwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")

# 🔹 Callback für Inline-Buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende eine Nachricht in dem Thema, das du sperren möchtest.", reply_markup=get_back_button())

    elif query.data == "remove_topic":
        cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine Themen gesperrt.", reply_markup=get_back_button())
            return

        keyboard = [[InlineKeyboardButton(f"🗂 Thema {topic[0]}", callback_data=f"confirm_remove_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text("🗑 **Wähle ein Thema zum Entfernen:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_remove_"):
        topic_id = int(query.data.replace("confirm_remove_", ""))
        cursor.execute("DELETE FROM allowed_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()
        await query.message.edit_text(f"✅ Thema {topic_id} wurde entfernt.", reply_markup=get_back_button(), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        if topics:
            response = "📋 **Gesperrte Themen:**\n" + "\n".join(f"🗂 Thema {topic[0]}" for topic in topics)
        else:
            response = "❌ Keine gesperrten Themen."
        await query.message.edit_text(response, reply_markup=get_back_button(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# 🔹 Zurück-Button für das Menü
def get_back_button():
    keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)

# 🔹 Nachrichten-Handler für das Hinzufügen von Themen
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    topic_id = update.message.message_thread_id  # Thema-ID
    
    if "action" in context.user_data and context.user_data["action"] == "add_topic":
        context.user_data.pop("action")

        cursor.execute("INSERT OR IGNORE INTO allowed_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
        conn.commit()
        await update.message.reply_text(f"✅ Thema {topic_id} wurde gesperrt.")
        return await show_menu(update, context)

# 🔹 Nachrichten-Filter (löscht Textnachrichten in gesperrten Themen)
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.is_topic_message:
        chat_id = update.message.chat_id
        topic_id = update.message.message_thread_id  # Thema-ID

        if is_topic_restricted(chat_id, topic_id):
            if not (update.message.photo or update.message.video or update.message.document):
                await update.message.delete()  # Nachricht löschen

# 🔹 Bot starten
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("mediabot", show_menu))

    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler
    application.add_handler(MessageHandler(filters.ALL, filter_messages))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("🤖 Medien-Bot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()