import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7714790321:AAFEyiy0PExl2oyCTuwCeNXJTd8i9B8pLP8"

# --- Datenbankverbindung für Gruppen-Whitelist ---
WHITELIST_DB_PATH = "/root/cpkiller/whitelist.db"
conn_whitelist = sqlite3.connect(WHITELIST_DB_PATH, check_same_thread=False)
cursor_whitelist = conn_whitelist.cursor()

# Prüft, ob die Gruppe für den Read-Only-Bot erlaubt ist
def is_group_allowed(chat_id):
    cursor_whitelist.execute("SELECT allow_ReadOnlyBot FROM allowed_groups WHERE chat_id = ? AND allow_ReadOnlyBot = 1", (chat_id,))
    return cursor_whitelist.fetchone() is not None

# --- Datenbank für gesperrte Themen ---
def init_db():
    conn = sqlite3.connect("/root/readonlybot.db", check_same_thread=False)  # Datenbankpfad korrigiert
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
        await update.message.reply_text("🚫 Diese Gruppe ist nicht für den Read-Only-Bot freigeschaltet!")
        return

    user_id = update.effective_user.id
    if not await is_admin(update, user_id):
        await update.message.reply_text("🚫 Du musst Admin sein, um dieses Menü zu öffnen!")
        return

    await update.message.reply_text("📷 Read-Only Themen-Verwaltung:", reply_markup=get_menu())

# --- Nutzer-Eingabe für Themen-ID (Fehler behoben & Debug hinzugefügt) ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not is_group_allowed(chat_id):
        return

    if "action" in context.user_data:
        action = context.user_data.pop("action")

        if action == "add_topic":
            try:
                topic_id = int(update.message.text.strip())
                print(f"📌 Versuche, Thema {topic_id} für Chat {chat_id} in die Datenbank einzutragen...")

                cursor.execute("INSERT INTO restricted_topics (chat_id, topic_id) VALUES (?, ?)", (chat_id, topic_id))
                conn.commit()

                print(f"✅ Thema {topic_id} wurde erfolgreich gespeichert!")
                await update.message.reply_text(f"✅ Thema {topic_id} gesperrt.")
            
            except sqlite3.IntegrityError:
                print(f"⚠️ Thema {topic_id} existiert bereits in der Datenbank!")
                await update.message.reply_text("❌ Thema existiert bereits.")

            except ValueError:
                print("❌ Ungültige Eingabe! Der Nutzer hat keine gültige Themen-ID gesendet.")
                await update.message.reply_text("❌ Ungültige Eingabe! Bitte sende eine gültige Themen-ID.")

            except Exception as e:
                print(f"❌ Fehler beim Eintragen in die Datenbank: {e}")
                await update.message.reply_text("❌ Ein unerwarteter Fehler ist aufgetreten.")

            return await show_menu(update, context)

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("readonly", show_menu))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("🤖 Read-Only Bot läuft mit Whitelist-Prüfung...")
    application.run_polling()

if __name__ == "__main__":
    main()