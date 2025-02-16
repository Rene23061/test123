import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

# --- Datenbankverbindung ---
def init_db():
    conn = sqlite3.connect("noreadbot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restricted_topics (
            chat_id INTEGER,
            topic_id INTEGER,
            PRIMARY KEY (chat_id, topic_id)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Admin-Prüfung ---
async def is_admin(update: Update, user_id: int) -> bool:
    chat_member = await update.effective_chat.get_member(user_id)
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# --- Menü erstellen ---
def get_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Thema sperren", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entsperren", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Menü anzeigen (mit Admin-Prüfung) ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(update, user_id):
        await update.message.reply_text("🚫 Du musst Admin sein, um dieses Menü zu öffnen!")
        return

    msg = await update.message.reply_text("🔒 Themen-Management:", reply_markup=get_menu())
    context.user_data["menu_message_id"] = msg.message_id  # Speichert die Menü-ID
    context.user_data.pop("action", None)  # Setzt Aktionen zurück

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if not await is_admin(update, user_id):
        await query.answer("❌ Nur Admins können diese Aktion ausführen!", show_alert=True)
        return

    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Sende die ID des Themas, das du sperren möchtest:", reply_markup=get_menu())

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gesperrten Themen.", reply_markup=get_menu())
            return

        keyboard = [[InlineKeyboardButton(f"Thema {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        await query.message.edit_text("🔓 Wähle ein Thema zum Entsperren:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("confirm_del_"):
        topic_id = int(query.data.replace("confirm_del_", ""))
        cursor.execute("DELETE FROM restricted_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()
        await query.message.edit_text(f"✅ Thema {topic_id} entsperrt.", reply_markup=get_menu())

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        text = "📋 **Gesperrte Themen:**\n" + "\n".join(f"- Thema {topic[0]}" for topic in topics) if topics else "❌ Keine gesperrten Themen."
        await query.message.edit_text(text, reply_markup=get_menu())

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        if "menu_message_id" in context.user_data:
            try:
                await context.bot.delete_message(chat_id, context.user_data["menu_message_id"])
            except:
                pass
        await query.message.delete()
        context.user_data.pop("action", None)  # Setzt Aktionen zurück

# --- Nutzer-Eingabe für Themen-ID ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            try:
                topic_id = int(text)
                cursor.execute("INSERT INTO restricted_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema {topic_id} gesperrt.")
            except ValueError:
                await update.message.reply_text("❌ Ungültige Eingabe! Bitte sende eine gültige Themen-ID.")
            return await show_menu(update, context)

# --- Nachrichtenprüfung (löscht Texte & Medien) ---
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    topic_id = update.message.message_thread_id

    cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
    restricted_topics = {row[0] for row in cursor.fetchall()}

    if topic_id in restricted_topics and not await is_admin(update, user_id):
        await update.message.delete()

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("noread", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    # ✅ Fehlerhafte Filter wurden ersetzt ✅
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | 
        filters.Document.ALL | filters.Animation.ALL, handle_media
    ))

    print("🤖 NoReadBot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()