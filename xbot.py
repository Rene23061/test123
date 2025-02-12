import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# ✅ Admin-Liste (Telegram-IDs der Admins)
ADMIN_LIST = [123456789, 987654321]  # Ersetze mit echten Admin-IDs!

# Verbindung zur Datenbank herstellen
def connect_db():
    return sqlite3.connect('shop_database.db')

# ✅ Nutzer registrieren, falls nicht vorhanden (mit Gruppen-ID)
def register_user_if_not_exists(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()

    # Prüfen, ob der Nutzer in dieser Gruppe bereits existiert
    cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, chat_id, username, first_name, last_name, 0))
        conn.commit()

    conn.close()

# ✅ Guthaben des Nutzers abrufen
def get_user_coins(user_id, chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# ✅ Benutzer-Info (TEST-ZWECKE)
async def user_info(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    coins = get_user_coins(user.id, chat_id)

    info_text = (
        f"🔍 **Benutzer-Check**\n"
        f"👤 **ID:** `{user.id}`\n"
        f"👥 **Gruppe:** `{chat_id}`\n"
        f"💰 **Guthaben:** `{coins} Coins`\n"
    )

    await update.message.reply_text(info_text, parse_mode="Markdown")

# ✅ Benutzerkonto-Menü jetzt **automatisch** im Privat-Chat öffnen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    private_chat_id = user.id

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    # ✅ Begrüßungstext
    welcome_text = (
        f"👤 **Benutzerkonto für {user.first_name}**\n"
        f"📌 **Gruppe:** `{chat_id}`\n"
        "Hier kannst du dein Guthaben verwalten.\n"
        "Wähle eine Option:"
    )

    # ✅ Inline-Keyboard mit Buttons
    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{chat_id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases_{chat_id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up_{chat_id}")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings_{chat_id}")],
        [InlineKeyboardButton("🔍 Nutzer-Check", callback_data=f"user_info_{chat_id}")]
    ]

    if user.id in ADMIN_LIST:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten (Admin)", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Direkt das Menü im Privat-Chat senden
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Start-Befehl für den Bot
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    await context.bot.send_message(chat_id=user.id, text="✅ Nutze /konto in deiner Gruppe, um dein Menü zu öffnen!")

# ✅ `/konto` wird automatisch zum Privat-Chat geleitet
async def konto_redirect(update: Update, context: CallbackContext):
    user = update.effective_user
    await user_account(update, context)

# ✅ Hauptfunktion zum Starten des Bots
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("konto", konto_redirect))
    app.add_handler(CommandHandler("user_info", user_info))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()