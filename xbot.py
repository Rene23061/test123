import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# 📌 Verbindung zur Datenbank herstellen
def connect_db():
    return sqlite3.connect('shop_database.db')

# 📌 Erstellt die Datenbank, falls sie nicht existiert
def initialize_database():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            coins INTEGER DEFAULT 0,
            PRIMARY KEY (id, chat_id)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Datenbank überprüft & initialisiert!")

# 📌 Nutzer in der Datenbank speichern
def save_user(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, 0)",
                   (user_id, chat_id, username, first_name, last_name))
    conn.commit()
    conn.close()

# 📌 Holt Nutzer aus einer bestimmten Gruppe
def get_users(chat_id, offset=0, limit=20):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name, coins FROM users WHERE chat_id = ? LIMIT ? OFFSET ?", (chat_id, limit, offset))
    users = cursor.fetchall()
    conn.close()
    return users

# 📌 Admin-Check
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# 📌 Benutzerkonto-Menü
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.message.chat_id
    private_chat_id = user.id

    save_user(user.id, chat_id, user.username, user.first_name, user.last_name)

    is_admin_user = await is_admin(context, user.id, chat_id)

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user.id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}_0")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text="👤 Dein Benutzerkonto:", reply_markup=reply_markup)

# 📌 Admin-Panel mit Paginierung
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    chat_id = int(data[2])
    offset = int(data[3])

    users = get_users(chat_id, offset)

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]} ({user[3]} Coins)", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]

    if offset > 0:
        keyboard.append([InlineKeyboardButton("⏪ Zurück", callback_data=f"admin_manage_{chat_id}_{offset - 20}")])
    if len(users) == 20:
        keyboard.append([InlineKeyboardButton("Weiter ⏩", callback_data=f"admin_manage_{chat_id}_{offset + 20}")])

    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_back_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔹 Wähle einen Nutzer:", reply_markup=reply_markup)

# 📌 Suchfunktion
async def search_user(update: Update, context: CallbackContext):
    query = update.message.text
    chat_id = update.message.chat_id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ? AND (username LIKE ? OR first_name LIKE ?)", (chat_id, f"%{query}%", f"%{query}%"))
    users = cursor.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text("❌ Kein Nutzer gefunden.")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🔍 Suchergebnisse:", reply_markup=reply_markup)

# 📌 Guthaben-Optionen für einen Nutzer
async def admin_user(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    user_id = int(data[2])
    chat_id = int(data[3])

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"add_coins_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➖ Guthaben entfernen", callback_data=f"remove_coins_{user_id}_{chat_id}")],
        [InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_manage_{chat_id}_0")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("⚙️ Guthaben-Optionen:", reply_markup=reply_markup)

# 📌 Hauptfunktion
def main():
    initialize_database()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", user_account))
    app.add_handler(CommandHandler("konto", user_account))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_user))
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))
    app.add_handler(CallbackQueryHandler(admin_user, pattern="^admin_user_"))

    print("✅ Bot gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()