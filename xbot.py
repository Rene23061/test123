import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank
def connect_db():
    return sqlite3.connect('shop_database.db')

# Nutzer registrieren, falls nicht vorhanden
def register_user_if_not_exists(user_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?)",
                       (user_id, username, first_name, last_name, 0))
        conn.commit()

    conn.close()

# Benutzerkonto-Menü anzeigen
def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    register_user_if_not_exists(user.id, user.username, user.first_name, user.last_name)

    # Begrüßungstext
    welcome_text = (
        f"👤 **Benutzerkonto für {user.first_name}**\n"
        "Hier kannst du dein Guthaben verwalten und deine Käufe einsehen.\n"
        "Wähle eine Option:"
    )

    # Inline-Keyboard mit Buttons
    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data="show_balance")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# Button-Klicks verarbeiten
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    # Nutzer prüfen & registrieren, falls nicht vorhanden
    register_user_if_not_exists(user.id, user.username, user.first_name, user.last_name)

    if query.data == "show_balance":
        query.edit_message_text(text="📊 Dein aktuelles Guthaben: 0 Coins (Funktion bald verfügbar!)")
    elif query.data == "show_purchases":
        query.edit_message_text(text="📜 Deine Käufe sind bald einsehbar!")
    elif query.data == "top_up":
        query.edit_message_text(text="💳 Guthaben aufladen wird bald freigeschaltet!")
    elif query.data == "settings":
        query.edit_message_text(text="🛠 Einstellungen sind bald verfügbar!")

# Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Befehle registrieren
    dp.add_handler(CommandHandler("konto", user_account))  # Benutzerkonto-Menü
    dp.add_handler(CallbackQueryHandler(button_handler))  # Button-Klicks verarbeiten

    # Bot starten
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
