import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# --- Telegram-Bot-Token ---
TOKEN = "8069716549:AAGfRNlsOIOlsMBZrAcsiB_IjV5yz3XOM8A"

# --- Verbindung zur SQLite-Datenbank ---
def init_db():
    conn = sqlite3.connect("/root/mediaonlybot/mediaonly.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_only_topics (
            chat_id INTEGER,
            topic_id INTEGER,
            PRIMARY KEY (chat_id, topic_id)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob User Admin/Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int) -> bool:
    chat_id = update.effective_chat.id
    member = await update.effective_chat.get_member(user_id)
    return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]

# --- Menü erstellen ---
def get_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Thema hinzufügen", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entfernen", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(update, user_id):
        await update.message.reply_text("❌ Du bist kein Admin und kannst das Menü nicht nutzen.")
        return

    if update.message:
        await update.message.reply_text("📜 **Themenverwaltung:**", reply_markup=get_menu(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text("📜 **Themenverwaltung:**", reply_markup=get_menu(), parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if not await is_admin(update, user_id):
        await query.answer("❌ Du bist kein Admin!", show_alert=True)
        return

    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Themen-ID**, die nur Medien erlauben soll:", reply_markup=get_menu())

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine Themen gespeichert.", reply_markup=get_menu(), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(str(topic[0]), callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text("🗑 **Wähle ein Thema zum Entfernen:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_to_delete = int(query.data.replace("confirm_del_", ""))
        keyboard = [
            [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_{topic_to_delete}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="del_topic")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"⚠️ Sicher, dass du das Thema **{topic_to_delete}** entfernen möchtest?",
                                      reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        topic_to_delete = int(query.data.replace("delete_", ""))
        cursor.execute("DELETE FROM media_only_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_to_delete))
        conn.commit()

        if cursor.rowcount > 0:
            await query.message.edit_text(f"✅ Thema entfernt: {topic_to_delete}", reply_markup=get_menu(), parse_mode="Markdown")
        else:
            await query.message.edit_text("⚠️ Thema war nicht gespeichert.", reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        if topics:
            response = "📜 **Gespeicherte Themen:**\n" + "\n".join(f"- {topic[0]}" for topic in topics)
        else:
            response = "❌ Keine Themen gespeichert."
        await query.message.edit_text(response, reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Nachrichten-Handler für Themen-ID Speicherung ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            try:
                topic_id = int(text)
                cursor.execute("INSERT INTO media_only_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema hinzugefügt: {topic_id}")
            except ValueError:
                await update.message.reply_text("❌ Ungültige Themen-ID! Bitte sende eine Zahl.")
            except sqlite3.IntegrityError:
                await update.message.reply_text("⚠️ Thema ist bereits gespeichert.")
            return await show_menu(update, context)

# --- Medien-Filter (Löscht alles außer Medien) ---
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    topic_id = message.message_thread_id

    cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
    restricted_topics = {row[0] for row in cursor.fetchall()}

    if topic_id in restricted_topics:
        if not (message.photo or message.video):
            await message.delete()
            return

# --- Hauptfunktion ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("mediaonlybot", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler für Eingaben
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    # Medien-Filter
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_messages))

    print("🤖 Media-Only-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()