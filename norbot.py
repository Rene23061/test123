import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Datenbankverbindung ---
def init_db():
    conn = sqlite3.connect("noreadbot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocked_topics (
            chat_id INTEGER,
            topic_id INTEGER,
            PRIMARY KEY (chat_id, topic_id)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Thema gesperrt ist ---
def is_topic_blocked(chat_id, topic_id):
    cursor.execute("SELECT 1 FROM blocked_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
    return cursor.fetchone() is not None

# --- Admin-Check ---
async def is_admin(update: Update, user_id: int) -> bool:
    chat_member = await update.effective_chat.get_member(user_id)
    return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- Menü-Buttons ---
def get_menu():
    keyboard = [
        [InlineKeyboardButton("🚫 Thema sperren", callback_data="add_topic")],
        [InlineKeyboardButton("✅ Thema entsperren", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text("❌ Nur Admins und Gruppeninhaber können dieses Menü nutzen!")
        return

    await update.message.reply_text("🔒 **Themen-Sperrverwaltung:**", reply_markup=get_menu(), parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    await query.answer()

    if not await is_admin(update, user_id):
        await query.message.edit_text("❌ Nur Admins und Gruppeninhaber können dieses Menü nutzen!")
        return

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Themen-ID**, die du sperren möchtest.", reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM blocked_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("✅ Es gibt keine gesperrten Themen.", reply_markup=get_menu(), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(f"ID: {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        await query.message.edit_text("🗑 **Wähle ein Thema zum Entsperren:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_id = int(query.data.replace("confirm_del_", ""))
        keyboard = [
            [InlineKeyboardButton("✅ Ja, entsperren", callback_data=f"delete_{topic_id}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="del_topic")]
        ]
        await query.message.edit_text(f"⚠️ Sicher, dass du das Thema {topic_id} entsperren möchtest?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        topic_id = int(query.data.replace("delete_", ""))
        cursor.execute("DELETE FROM blocked_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()
        await query.message.edit_text(f"✅ Thema **{topic_id}** entsperrt!", reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM blocked_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        response = "📋 **Gesperrte Themen:**\n" + "\n".join(f"- ID: {topic[0]}" for topic in topics) if topics else "❌ Keine gesperrten Themen."
        await query.message.edit_text(response, reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Themen-ID speichern ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            if text.isdigit():
                topic_id = int(text)
                try:
                    cursor.execute("INSERT INTO blocked_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                    conn.commit()
                    await update.message.reply_text(f"✅ Thema **{topic_id}** gesperrt!")
                except sqlite3.IntegrityError:
                    await update.message.reply_text("⚠️ Dieses Thema ist bereits gesperrt.")
            else:
                await update.message.reply_text("❌ Ungültige ID! Bitte sende eine **numerische** Themen-ID.")
            return await show_menu(update, context)

# --- Nachrichten filtern & blockieren ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    topic_id = message.message_thread_id  # Themen-ID ermitteln

    if not topic_id:
        return  # Kein Thema erkannt, Nachricht ignorieren

    # Admins & Gruppeninhaber dürfen immer schreiben
    if await is_admin(update, user_id):
        return

    # Nachricht löschen, wenn das Thema gesperrt ist
    if is_topic_blocked(chat_id, topic_id):
        await context.bot.delete_message(chat_id, message.message_id)
        await context.bot.send_message(
            chat_id,
            f"🚫 @{message.from_user.username}, dieses Thema ist gesperrt!",
            parse_mode="Markdown"
        )

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle & Inline-Buttons
    application.add_handler(CommandHandler("noread", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    application.add_handler(MessageHandler(filters.ALL, handle_messages))

    print("🤖 No Read Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()