import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

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

# Benutzerkonto-Menü anzeigen (JETZT IM PRIVAT-CHAT)
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Gruppen-ID holen
    private_chat_id = user.id  # Nutzer-ID für privaten Chat

    # Nutzer registrieren mit Gruppen-ID
    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    # Begrüßungstext
    welcome_text = (
        f"👤 **Benutzerkonto für {user.first_name}**\n"
        "Hier kannst du dein Guthaben verwalten und deine Käufe einsehen.\n"
        f"📌 **Du kommst aus der Gruppe:** `{chat_id}`\n"
        "Wähle eine Option:"
    )

    # Inline-Keyboard mit Buttons
    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{chat_id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases_{chat_id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up_{chat_id}")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Menü als private Nachricht senden
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

    # Bestätigung in der Gruppe senden (optional)
    await update.message.reply_text(f"📩 {user.first_name}, ich habe dir dein Konto-Menü privat gesendet. Schau in deinen Chat mit mir!")

# Button-Klicks verarbeiten
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    private_chat_id = user.id  # Privat-Chat-ID
    callback_data = query.data.split("_")
    action = callback_data[0]
    chat_id = callback_data[1]  # Gruppen-ID aus Callback

    # Nutzer prüfen & registrieren, falls nicht vorhanden
    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    if action == "show_balance":
        await query.edit_message_text(text=f"📊 Dein aktuelles Guthaben für Gruppe `{chat_id}`: 0 Coins (Funktion bald verfügbar!)")
    elif action == "show_purchases":
        await query.edit_message_text(text="📜 Deine Käufe sind bald einsehbar!")
    elif action == "top_up":
        await query.edit_message_text(text="💳 Guthaben aufladen wird bald freigeschaltet!")
    elif action == "settings":
        await query.edit_message_text(text="🛠 Einstellungen sind bald verfügbar!")

# Start-Befehl für den Bot (nutzt private Nachricht)
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Gruppen-ID holen

    # Nutzer registrieren
    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)

    await context.bot.send_message(chat_id=user.id, text="✅ Nutze /konto in deiner Gruppe, um dein Menü zu öffnen!")

# Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    app = Application.builder().token(TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))  # Start-Befehl
    app.add_handler(CommandHandler("konto", user_account))  # Benutzerkonto-Menü
    app.add_handler(CallbackQueryHandler(button_handler))  # Button-Klicks verarbeiten

    # Bot starten
    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()