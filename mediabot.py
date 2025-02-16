import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8069716549:AAGfRNlsOIOlsMBZrAcsiB_IjV5yz3XOM8A"

# --- Sicherstellen, dass der Ordner existiert ---
DB_FOLDER = "/root/mediabot"
DB_PATH = os.path.join(DB_FOLDER, "mediabot.db")

if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)  # Falls der Ordner nicht existiert, erstelle ihn

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# --- Prüfen, ob der Benutzer ein Admin ist ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)

    return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# --- Menü erstellen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Nur Admins können das Menü verwenden!")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Thema hinzufügen", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entfernen", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("🎛 **Medien-Only Bot Menü**", reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text("🎛 **Medien-Only Bot Menü**", reply_markup=reply_markup, parse_mode="Markdown")

# --- Callback für Inline-Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "add_topic":
        context.user_data["action"] = "add_topic"
        await query.message.edit_text("📩 Bitte sende die **Themen-ID**, die du hinzufügen möchtest.", reply_markup=get_back_menu())

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gespeicherten Themen.", reply_markup=get_back_menu(), parse_mode="Markdown")
            return

        keyboard = [[InlineKeyboardButton(f"Thema {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text("🗑 **Wähle ein Thema zum Löschen:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_to_delete = int(query.data.replace("confirm_del_", ""))
        keyboard = [
            [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_{topic_to_delete}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="del_topic")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"⚠️ Bist du sicher, dass du Thema **{topic_to_delete}** löschen möchtest?", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        topic_to_delete = int(query.data.replace("delete_", ""))
        cursor.execute("DELETE FROM allowed_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_to_delete))
        conn.commit()

        if cursor.rowcount > 0:
            await query.message.edit_text(f"✅ Thema **{topic_to_delete}** wurde entfernt.", reply_markup=get_back_menu(), parse_mode="Markdown")
        else:
            await query.message.edit_text("⚠️ Thema war nicht in der Liste.", reply_markup=get_back_menu(), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        if topics:
            response = "📋 **Erlaubte Themen:**\n" + "\n".join(f"- {topic[0]}" for topic in topics)
        else:
            response = "❌ Keine Themen gespeichert."
        await query.message.edit_text(response, reply_markup=get_back_menu(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        await query.message.delete()

# --- Inline-Menü für Zurück-Button ---
def get_back_menu():
    keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)

# --- Nachrichten-Handler für Eingaben (Themen-ID) ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            try:
                topic_id = int(text)
                cursor.execute("INSERT INTO allowed_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema {topic_id} wurde hinzugefügt.")
            except sqlite3.IntegrityError:
                await update.message.reply_text("⚠️ Dieses Thema ist bereits gespeichert.")
            except ValueError:
                await update.message.reply_text("❌ Ungültige Themen-ID! Bitte sende eine Zahl.")
            return await show_menu(update, context)

# --- Nachrichtenkontrolle (nur Medien erlauben, ohne Text) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    topic_id = message.message_thread_id if message.is_topic_message else None

    if topic_id:
        cursor.execute("SELECT topic_id FROM allowed_topics WHERE chat_id = ?", (chat_id,))
        allowed_topics = {row[0] for row in cursor.fetchall()}

        if topic_id in allowed_topics:
            if message.text or (not message.photo and not message.video):
                await message.delete()
                return

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Befehle
    application.add_handler(CommandHandler("mediabot", show_menu))

    # Callback für Inline-Buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Nachrichten-Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    application.add_handler(MessageHandler(filters.ALL, kontrolliere_nachricht))

    print("🤖 Medien-Only Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()