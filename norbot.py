import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

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

# --- Prüfen, ob der Benutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int) -> bool:
    """Holt die Admin-Liste der Gruppe und prüft, ob der Nutzer darin ist."""
    chat = update.effective_chat
    member = await chat.get_member(user_id)

    return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt das Inline-Menü für das Sperren/Löschen von Themen."""
    keyboard = [
        [InlineKeyboardButton("➕ Thema sperren", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entsperren", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("🔒 **Themen-Verwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text("🔒 **Themen-Verwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")

# --- Callback für Inline-Menü ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Themen-ID**, die du sperren möchtest:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]))

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gesperrten Themen.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(f"🗑 Thema {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text("🗑 **Wähle ein Thema zum Entsperren:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_to_delete = int(query.data.replace("confirm_del_", ""))
        cursor.execute("DELETE FROM topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_to_delete))
        conn.commit()
        await query.message.edit_text(f"✅ Thema {topic_to_delete} entsperrt.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")

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

# --- Themen hinzufügen ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            try:
                topic_id = int(text)
                cursor.execute("INSERT INTO topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema {topic_id} gesperrt.")
            except ValueError:
                await update.message.reply_text("❌ Ungültige Themen-ID! Bitte sende eine Zahl.")
            return await show_menu(update, context)

# --- Nachrichten-Handler für gesperrte Themen ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    topic_id = message.message_thread_id  # Thema-ID der Nachricht
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    # Prüfen, ob das Thema gesperrt ist
    if topic_id and is_topic_restricted(chat_id, topic_id):
        if not await is_admin(update, user_id):  # Admins dürfen schreiben
            await message.delete()
            await context.bot.send_message(
                chat_id,
                f"🚫 {username}, du kannst hier nicht schreiben!",
                reply_to_message_id=message.message_id
            )

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("noread", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler für gesperrte Themen
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    # Benutzereingaben für Themen-IDs
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_user_input))

    print("🤖 Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()