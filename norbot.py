import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7847601238:AAF9MNu25OVGwkHUDCopgIqZ-LzWhxB4__Y"

# --- Verbindung zur SQLite-Datenbank herstellen ---
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

# --- Prüfen, ob ein Nutzer Admin oder Gruppeninhaber ist ---
async def is_admin(update: Update, user_id: int):
    try:
        chat_member = await update.effective_chat.get_member(user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text("⛔ Nur Admins oder der Gruppeninhaber können dieses Menü nutzen.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Thema sperren", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entsperren", callback_data="remove_topic")],
        [InlineKeyboardButton("📋 Gesperrte Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text("🔒 **Themen-Verwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data["last_menu_message"] = message.message_id

# --- Callback für Inline-Menü ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    await query.answer()

    if not await is_admin(update, user_id):
        await query.message.reply_text("⛔ Nur Admins oder der Gruppeninhaber können dieses Menü nutzen.")
        return

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Topic-ID**, die du sperren möchtest:")

    elif query.data == "remove_topic":
        cursor.execute("SELECT topic_id FROM blocked_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gesperrten Themen vorhanden.", parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(f"📌 {topic[0]}", callback_data=f"confirm_remove_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🗑 **Wähle ein Thema zum Entsperren:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_remove_"):
        topic_to_remove = int(query.data.replace("confirm_remove_", ""))
        cursor.execute("DELETE FROM blocked_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_to_remove))
        conn.commit()
        await query.message.edit_text(f"✅ Thema `{topic_to_remove}` entsperrt.", parse_mode="Markdown")
        await show_menu(update, context)

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM blocked_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        if topics:
            response = "📋 **Gesperrte Themen:**\n" + "\n".join(f"- `{topic[0]}`" for topic in topics)
        else:
            response = "❌ Keine gesperrten Themen vorhanden."
        await query.message.edit_text(response, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")]]), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Thema hinzufügen ---
async def handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data and context.user_data["action"] == "add_topic":
        context.user_data.pop("action")

        try:
            topic_id = int(text)
            cursor.execute("INSERT INTO blocked_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
            conn.commit()
            await update.message.reply_text(f"✅ Thema `{topic_id}` wurde gesperrt.")
        except ValueError:
            await update.message.reply_text("❌ Ungültige Eingabe! Bitte gib eine **numerische Topic-ID** ein.")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ Dieses Thema ist bereits gesperrt.")

# --- Nachrichten in gesperrten Themen löschen ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    topic_id = update.message.message_thread_id if update.message.is_topic_message else None
    user_id = update.message.from_user.id

    if topic_id and not await is_admin(update, user_id):
        cursor.execute("SELECT topic_id FROM blocked_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        if cursor.fetchone():
            await update.message.delete()
            await update.message.reply_text(f"🚫 **Dieses Thema ist nur für Admins!**\nBitte schreibe in einem anderen Bereich.")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehl für Themen-Verwaltung
    application.add_handler(CommandHandler("noread", show_menu))
    
    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler für Themen-Sperre
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_input))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 NoReadBot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()
