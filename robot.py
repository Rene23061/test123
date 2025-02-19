import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7714790321:AAFEyiy0PExl2oyCTuwCeNXJTd8i9B8pLP8"

# --- Datenbankverbindung für Gruppen-Whitelist ---
WHITELIST_DB_PATH = "/root/cpkiller/whitelist.db"
conn_whitelist = sqlite3.connect(WHITELIST_DB_PATH, check_same_thread=False)
cursor_whitelist = conn_whitelist.cursor()

# --- Prüft, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id):
    cursor_whitelist.execute("SELECT allow_ReadOnlyBot FROM allowed_groups WHERE chat_id = ? AND allow_ReadOnlyBot = 1", (chat_id,))
    return cursor_whitelist.fetchone() is not None

# --- Datenbank für gesperrte Themen ---
def init_db():
    conn = sqlite3.connect("readonlybot.db", check_same_thread=False)
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

# --- Menü anzeigen ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not is_group_allowed(chat_id):
        await update.message.reply_text("🚫 Diese Gruppe ist nicht für den Text-Only-Bot freigeschaltet!")
        return

    user_id = update.effective_user.id
    if not await is_admin(update, user_id):
        await update.message.reply_text("🚫 Du musst Admin sein, um dieses Menü zu öffnen!")
        return

    msg = await update.message.reply_text("📄 Text-Only Themen-Verwaltung:", reply_markup=get_menu())
    context.user_data["bot_messages"] = [msg.message_id]

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
        new_text = "📩 Sende die ID des Themas, das du sperren möchtest:"

        if query.message.text != new_text:
            try:
                await query.message.edit_text(new_text, reply_markup=get_menu())
            except:
                pass

    elif query.data == "del_topic":
        cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()

        if not topics:
            await query.answer("❌ Keine gesperrten Themen.")
            return

        keyboard = [[InlineKeyboardButton(f"Thema {topic[0]}", callback_data=f"confirm_del_{topic[0]}")] for topic in topics]
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="back_to_menu")])

        try:
            await query.message.edit_text("🔓 Wähle ein Thema zum Entsperren:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass

    elif query.data.startswith("confirm_del_"):
        topic_id = int(query.data.replace("confirm_del_", ""))
        cursor.execute("DELETE FROM restricted_topics WHERE chat_id = ? AND topic_id = ?", (chat_id, topic_id))
        conn.commit()
        await query.answer(f"✅ Thema {topic_id} entsperrt.", show_alert=True)
        await show_menu(update, context)

    elif query.data == "list_topics":
        cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
        topics = cursor.fetchall()
        text = "📋 **Gesperrte Themen:**\n" + "\n".join(f"- Thema {topic[0]}" for topic in topics) if topics else "❌ Keine gesperrten Themen."

        try:
            await query.message.edit_text(text, reply_markup=get_menu())
        except:
            pass

    elif query.data == "close_menu":
        await query.message.delete()

# --- Themen-ID speichern ---
async def handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if "action" in context.user_data and context.user_data["action"] == "add_topic":
        try:
            topic_id = int(update.message.text)
            cursor.execute("INSERT INTO restricted_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
            conn.commit()
            await update.message.reply_text(f"✅ Thema {topic_id} wurde gesperrt.")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ Dieses Thema ist bereits gesperrt!")
        except ValueError:
            await update.message.reply_text("❌ Ungültige Themen-ID! Bitte eine Zahl eingeben.")
        except Exception as e:
            await update.message.reply_text(f"❌ Fehler: {str(e)}")

        context.user_data.pop("action", None)

# --- Nachrichtenprüfung (löscht alle Medien, erlaubt nur Text) ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not is_group_allowed(chat_id):
        return

    if update.message.photo or update.message.video or update.message.document or update.message.voice or update.message.audio or update.message.animation or update.message.sticker:
        await update.message.delete()
        return

    cursor.execute("SELECT topic_id FROM restricted_topics WHERE chat_id = ?", (chat_id,))
    restricted_topics = {row[0] for row in cursor.fetchall()}

    if update.message.message_thread_id in restricted_topics and not await is_admin(update, user_id):
        await update.message.delete()

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("readonly", show_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_input))
    application.add_handler(MessageHandler(filters.ALL, handle_user_input))

    print("🤖 Bot läuft mit Text-Only-Filter...")
    application.run_polling()

if __name__ == "__main__":
    main()