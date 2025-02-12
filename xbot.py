import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

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

# Prüft, ob der Nutzer Admin oder Gruppeninhaber ist
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]
    except:
        return False

# Benutzerkonto-Menü im Privat-Chat anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    private_chat_id = user.id

    if user.is_bot:
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    is_admin_user = await is_admin(context, user.id, chat_id)

    welcome_text = (
        f"👤 Benutzerkonto für {user.first_name}\n"
        f"📌 Gruppe: {chat_id}\n"
        "Hier kannst du dein Guthaben verwalten.\n"
        "Wähle eine Option:"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage")])

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

# Admin-Panel öffnen (ohne erneuten Admin-Check)
async def admin_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    await context.bot.send_message(chat_id=user.id, text=f"⚙️ Admin-Panel geöffnet!")

# Hauptfunktion zum Starten des Bots
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", konto_redirect))  
    app.add_handler(CommandHandler("konto", konto_redirect))  
    app.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin_manage$"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()