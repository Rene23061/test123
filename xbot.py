import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# ✅ Test-Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# 📌 Verbindung zur Datenbank
def connect_db():
    return sqlite3.connect('shop_database.db')

# 📌 Datenbank initialisieren
def initialize_database():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            coins INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Datenbank überprüft & initialisiert!")

# 📌 Nutzer in der Datenbank speichern
def save_user(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, 0)",
                       (user_id, chat_id, username, first_name, last_name))
        conn.commit()
        print(f"✅ Neuer Nutzer {first_name} ({user_id}) in Gruppe {chat_id} gespeichert!")
    conn.close()

# 📌 Admin-Check
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Fehler bei Admin-Check: {e}")
        return False

# 📌 Startmenü für Nutzer
async def start_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.message.chat_id
    save_user(user.id, chat_id, user.username, user.first_name, user.last_name)

    keyboard = [
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")],
        [InlineKeyboardButton("👤 Account", callback_data="account"),
         InlineKeyboardButton("💳 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("📦 Gekaufte Inhalte", callback_data="purchases")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"👋 Willkommen, {user.first_name}! Wähle eine Option:", reply_markup=reply_markup)

# 📌 Wallet-Menü
async def wallet_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    keyboard = [
        [InlineKeyboardButton("💰 Guthaben hinzufügen", callback_data=f"add_balance_{user_id}")],
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user_id}")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("💳 **Wallet Menü**\nWähle eine Option:", reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Guthaben-Anzeige
async def show_balance(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    user_id = int(data[2])

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    balance = result[0] if result else 0

    await query.answer(f"💰 Dein Guthaben: {balance} Coins", show_alert=True)

# 📌 Admin-Menü für Nutzerverwaltung
async def admin_manage_users(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    users = get_all_users(chat_id)

    if not users:
        await query.message.edit_text("⚠️ Keine Nutzer gefunden!")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"user_select_{user[0]}_{chat_id}")]
                for user in users]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🔹 Wähle einen Nutzer zur Verwaltung:", reply_markup=reply_markup)

# 📌 Nutzerverwaltung für Admins
async def manage_user(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    user_id = int(data[2])
    chat_id = int(data[3])

    keyboard = [
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"add_balance_{user_id}")],
        [InlineKeyboardButton("➖ Guthaben entfernen", callback_data=f"remove_balance_{user_id}")],
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user_id}")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="admin_manage")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(f"📌 Verwaltung für `{user_id}` in Gruppe `{chat_id}`", reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Navigation zurück zum Hauptmenü
async def back_to_main(update: Update, context: CallbackContext):
    query = update.callback_query
    await start_menu(update, context)

# 📌 Holt alle Nutzer einer Gruppe
def get_all_users(chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    return users

# 📌 Hauptfunktion zum Starten des Bots
def main():
    initialize_database()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern="^wallet$"))
    app.add_handler(CallbackQueryHandler(show_balance, pattern="^show_balance_"))
    app.add_handler(CallbackQueryHandler(admin_manage_users, pattern="^admin_manage$"))
    app.add_handler(CallbackQueryHandler(manage_user, pattern="^user_select_"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^main_menu$"))

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()