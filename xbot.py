import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# ✅ Admin-Liste (Telegram-IDs der Admins)
ADMIN_LIST = [123456789, 987654321]  # Ersetze mit den echten Admin-IDs!

# Verbindung zur Datenbank herstellen
def connect_db():
    return sqlite3.connect('shop_database.db')

# Nutzer registrieren, falls nicht vorhanden (mit Gruppen-ID)
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

# Guthaben des Nutzers abrufen
def get_user_coins(user_id, chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# ✅ Benutzerkonto-Menü jetzt NUR im PRIVAT-CHAT anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Gruppen-ID holen
    private_chat_id = user.id  # Nutzer-ID für privaten Chat

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    # Begrüßungstext
    welcome_text = (
        f"👤 **Benutzerkonto für {user.first_name}**\n"
        f"📌 **Gruppe:** `{chat_id}`\n"
        "Hier kannst du dein Guthaben verwalten und deine Käufe einsehen.\n"
        "Wähle eine Option:"
    )

    # Inline-Keyboard mit Buttons
    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{chat_id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases_{chat_id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up_{chat_id}")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings_{chat_id}")]
    ]

    # ✅ Falls der Nutzer ein Admin ist, füge den Admin-Button hinzu
    if user.id in ADMIN_LIST:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten (Admin)", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Direkt das Menü im Privat-Chat senden
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Admin-Menü für Guthabenverwaltung
async def admin_menu(update: Update, context: CallbackContext, chat_id):
    user = update.effective_user

    # 🔹 Prüfen, ob der Nutzer Admin ist
    if user.id not in ADMIN_LIST:
        await context.bot.send_message(chat_id=user.id, text="⛔ **Du bist kein Admin!**\nDiese Funktion ist nur für Administratoren verfügbar.")
        return

    # 🔹 Falls Admin → Admin-Menü anzeigen
    keyboard = [
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"add_coins_{chat_id}")],
        [InlineKeyboardButton("➖ Guthaben abziehen", callback_data=f"remove_coins_{chat_id}")],
        [InlineKeyboardButton("⬅️ Zurück", callback_data=f"show_balance_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=user.id, text="⚙️ **Admin-Guthabenverwaltung**\nWähle eine Option:", reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Button-Klicks verarbeiten
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    private_chat_id = user.id  # Privat-Chat-ID
    callback_data = query.data.split("_")
    action = callback_data[0]
    chat_id = callback_data[1]  # Gruppen-ID aus Callback

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    if action == "show_balance":
        coins = get_user_coins(user.id, chat_id)
        await query.edit_message_text(text=f"📊 Dein aktuelles Guthaben für Gruppe `{chat_id}`: **{coins} Coins**")
    elif action == "show_purchases":
        await query.edit_message_text(text="📜 Deine Käufe sind bald einsehbar!")
    elif action == "top_up":
        await query.edit_message_text(text="💳 Guthaben aufladen wird bald freigeschaltet!")
    elif action == "settings":
        await query.edit_message_text(text="🛠 Einstellungen sind bald verfügbar!")
    elif action == "admin_manage":
        await admin_menu(update, context, chat_id)

# ✅ Start-Befehl für den Bot (nur im Privat-Chat)
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Gruppen-ID holen

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    await context.bot.send_message(chat_id=user.id, text="✅ Nutze /konto in deiner Gruppe, um dein Menü zu öffnen!")

# ✅ Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    app = Application.builder().token(TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))  # Start-Befehl
    app.add_handler(CommandHandler("konto", user_account))  # Benutzerkonto-Menü (NUR PRIVAT-CHAT)
    app.add_handler(CallbackQueryHandler(button_handler))  # Button-Klicks verarbeiten

    # Bot starten
    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()