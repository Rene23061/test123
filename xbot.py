import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank herstellen
def connect_db():
    return sqlite3.connect('shop_database.db')

# ✅ Nutzer registrieren, falls nicht vorhanden (mit Gruppen-ID)
def register_user_if_not_exists(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, chat_id, username, first_name, last_name, 0))
        conn.commit()
    conn.close()

# ✅ Alle Nutzer einer Gruppe abrufen (für Admin-Panel)
def get_all_users(chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    return users

# ✅ Guthaben eines Nutzers abrufen
def get_user_coins(user_id, chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# ✅ Prüft, ob der Nutzer Admin oder Gruppeninhaber ist
async def is_admin(update: Update, context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]
    except Exception:
        return False

# ✅ Benutzerkonto-Menü im Privat-Chat anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    private_chat_id = user.id

    if user.is_bot:
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    is_admin_user = await is_admin(update, context, user.id, chat_id)

    welcome_text = (
        f"👤 **Benutzerkonto für {user.first_name}**\n"
        f"📌 **Gruppe:** `{chat_id}`\n"
        "Hier kannst du dein Guthaben verwalten.\n"
        "Wähle eine Option:"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{chat_id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases_{chat_id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up_{chat_id}")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings_{chat_id}")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ✅ `/konto` wird automatisch zum Privat-Chat geleitet
async def konto_redirect(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.is_bot:
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    await user_account(update, context)

# ✅ Admin-Panel: Nutzerliste anzeigen
async def admin_menu(update: Update, context: CallbackContext, chat_id):
    user = update.effective_user
    is_admin_user = await is_admin(update, context, user.id, chat_id)

    if not is_admin_user:
        await context.bot.send_message(chat_id=user.id, text="⛔ **Du bist kein Admin!**")
        return

    users = get_all_users(chat_id)
    keyboard = [[InlineKeyboardButton(f"{u[1]}", callback_data=f"manage_user_{u[0]}_{chat_id}")] for u in users]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"show_balance_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user.id, text="⚙️ **Wähle einen Nutzer zur Guthabenverwaltung:**", reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Nutzer-Verwaltungsmenü anzeigen
async def manage_user(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    user_id, chat_id = data[2], data[3]

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"check_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"add_coins_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➖ Guthaben abziehen", callback_data=f"remove_coins_{user_id}_{chat_id}")],
        [InlineKeyboardButton("⬅️ Zurück", callback_data=f"admin_manage_{chat_id}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text="⚙️ **Guthaben-Optionen für diesen Nutzer:**", reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Hauptfunktion zum Starten des Bots
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("konto", konto_redirect))
    app.add_handler(CallbackQueryHandler(manage_user, pattern="^manage_user_"))
    app.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin_manage_"))

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()