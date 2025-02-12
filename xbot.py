import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank herstellen
def connect_db():
    return sqlite3.connect('shop_database.db')

# Nutzer registrieren, falls nicht vorhanden
def register_user_if_not_exists(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, chat_id, username, first_name, last_name, 0))
        conn.commit()
    conn.close()

# Holt alle Nutzer der Gruppe
def get_all_users(chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    return users

# Prüft, ob der Nutzer Admin oder Gruppeninhaber ist
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        print(f"[DEBUG] Admin-Check für {user_id} in Chat {chat_id} - Status: {chat_member.status}")
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Fehler bei Admin-Check für {user_id} in Chat {chat_id}: {e}")
        return False

# Holt Guthaben eines Nutzers
def get_user_balance(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
    balance = cursor.fetchone()
    conn.close()
    return balance[0] if balance else 0

# Ändert Guthaben eines Nutzers
def update_user_balance(user_id, amount):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# Benutzerkonto-Menü im Privat-Chat anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    private_chat_id = user.id

    if user.is_bot:
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    is_admin_user = await is_admin(context, user.id, chat_id)

    print(f"[DEBUG] /konto aufgerufen von {user.id} in Chat {chat_id}, Admin: {is_admin_user}")

    welcome_text = f"👤 Benutzerkonto für {user.first_name}\n📌 Gruppe: {chat_id}\nHier kannst du dein Guthaben verwalten."

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user.id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# /konto wird automatisch zum Privat-Chat geleitet
async def konto_redirect(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.is_bot:
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    await user_account(update, context)

# **ADMIN: Holt ALLE Nutzer aus der Gruppe und zeigt sie als Buttons**
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split("_")[1]

    print(f"[DEBUG] Admin-Panel geöffnet in Gruppe {chat_id}")

    users = get_all_users(chat_id)
    
    if not users:
        await query.message.reply_text("⚠️ Keine Nutzer in der Datenbank gefunden!")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("🔹 Wähle einen Nutzer:", reply_markup=reply_markup)

# Zeigt Aktionen für den ausgewählten Nutzer
async def admin_user_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id, chat_id = query.data.split("_")[2], query.data.split("_")[3]

    keyboard = [
        [InlineKeyboardButton("💰 Guthaben anzeigen", callback_data=f"admin_show_{user_id}")],
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"admin_add_{user_id}")],
        [InlineKeyboardButton("➖ Guthaben abziehen", callback_data=f"admin_subtract_{user_id}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🔹 Wähle eine Aktion:", reply_markup=reply_markup)

# Zeigt Guthaben eines Nutzers an
async def admin_show_balance(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.data.split("_")[2]

    balance = get_user_balance(user_id)
    await query.message.reply_text(f"💰 Guthaben des Nutzers: {balance} Coins")

# Hauptfunktion zum Starten des Bots
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", konto_redirect))  
    app.add_handler(CommandHandler("konto", konto_redirect))  
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))  
    app.add_handler(CallbackQueryHandler(admin_user_actions, pattern="^admin_user_"))  
    app.add_handler(CallbackQueryHandler(admin_show_balance, pattern="^admin_show_"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()