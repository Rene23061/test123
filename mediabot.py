import os
import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8069716549:AAGfRNlsOIOlsMBZrAcsiB_IjV5yz3XOM8A"

# --- Datenbank-Setup ---
DB_FOLDER = "/root/mediabot"
DB_PATH = os.path.join(DB_FOLDER, "mediabot.db")

if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# --- URL-Pattern zur Erkennung von Links ---
URL_PATTERN = re.compile(
    r'((http|https):\/\/)?'  
    r'(www\.)?'              
    r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.'  
    r'[a-zA-Z0-9()]{1,6}\b'  
    r'([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'  
)

# --- Prüfen, ob der Benutzer ein Admin ist ---
async def is_admin(update: Update, user_id: int) -> bool:
    chat_member = await update.effective_chat.get_member(user_id)
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# --- Menü erstellen ---
def get_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Thema hinzufügen", callback_data="add_topic")],
        [InlineKeyboardButton("❌ Thema entfernen", callback_data="del_topic")],
        [InlineKeyboardButton("📋 Themen anzeigen", callback_data="list_topics")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Menü anzeigen (mit Admin-Prüfung) ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(update, user_id):
        await update.message.reply_text("🚫 Du musst Admin sein, um dieses Menü zu öffnen!")
        return
    
    msg = await update.message.reply_text("📷 **Medien-Only Bot Menü:**", reply_markup=get_menu(), parse_mode="Markdown")
    context.user_data["menu_message_id"] = msg.message_id  # Speichert die Menü-ID

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
        await query.message.edit_text("📩 Sende die **Themen-ID**, die du hinzufügen möchtest.", reply_markup=get_menu())

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.message.edit_text("❌ Keine gespeicherten Themen.", reply_markup=get_menu())
            return

        keyboard = [[InlineKeyboardButton(f"Thema {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])
        await query.message.edit_text("🗑 **Wähle ein Thema zum Entfernen:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("confirm_del_"):
        topic_id = int(query.data.replace("confirm_del_", ""))
        cursor.execute("DELETE FROM media_only_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()
        await query.message.edit_text(f"✅ Thema {topic_id} wurde entfernt.", reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        text = "📋 **Erlaubte Medien-Themen:**\n" + "\n".join(f"- Thema {topic[0]}" for topic in topics) if topics else "❌ Keine Themen gespeichert."
        await query.message.edit_text(text, reply_markup=get_menu(), parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_menu(update, context)

    elif query.data == "close_menu":
        if "menu_message_id" in context.user_data:
            try:
                await context.bot.delete_message(chat_id, context.user_data["menu_message_id"])
            except:
                pass
        await query.message.delete()

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
                cursor.execute("INSERT INTO media_only_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()
                await update.message.reply_text(f"✅ Thema {topic_id} wurde gespeichert.")
            except ValueError:
                await update.message.reply_text("❌ Ungültige Eingabe! Bitte sende eine gültige Themen-ID.")
            return await show_menu(update, context)

# --- Nachrichtenkontrolle (Nur Medien erlauben) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    topic_id = message.message_thread_id if message.is_topic_message else None

    if topic_id:
        cursor.execute("SELECT topic_id FROM media_only_topics WHERE chat_id = ?", (chat_id,))
        allowed_topics = {row[0] for row in cursor.fetchall()}

        if topic_id in allowed_topics:
            ist_reiner_text = bool(message.text and not message.photo and not message.video and not message.animation)
            enthaelt_link = bool(message.text and URL_PATTERN.search(message.text))

            if ist_reiner_text or enthaelt_link:
                try:
                    await message.delete()
                    print(f"❌ Nachricht von {user_id} gelöscht (Thema {topic_id})")
                except Exception as e:
                    print(f"⚠ Fehler beim Löschen: {e}")

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("mediabot", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Medien-Only Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()