import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Bot-Token
TOKEN = "7507729922:AAHLtY0h7rYMswxm2OVWnK3W-cq5-A4cXVQ"

# Verbindung zur Datenbank herstellen
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
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
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

    await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# Button-Klicks verarbeiten
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    # Nutzer prüfen & registrieren, falls nicht vorhanden
    register_user_if_not_exists(user.id, user.username, user.first_name, user.last_name)

    if query.data == "show_balance":
        await query.edit_message_text(text="📊 Dein aktuelles Guthaben: 0 Coins (Funktion bald verfügbar!)")
    elif query.data == "show_purchases":
        await query.edit_message_text(text="📜 Deine Käufe sind bald einsehbar!")
    elif query.data == "top_up":
        await query.edit_message_text(text="💳 Guthaben aufladen wird bald freigeschaltet!")
    elif query.data == "settings":
        await query.edit_message_text(text="🛠 Einstellungen sind bald verfügbar!")

# Start-Befehl für den Bot (öffnet Menü in der Gruppe, wenn Button gedrückt wird)
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    register_user_if_not_exists(user.id, user.username, user.first_name, user.last_name)

    # Prüfen, ob "groupmenu" als Argument übergeben wurde (durch den Button-Klick)
    if context.args and context.args[0] == "groupmenu":
        await user_account(update, context)  # Direkt das Menü in die Gruppe senden
    else:
        await context.bot.send_message(chat_id=chat_id, text="✅ Willkommen! Nutze /konto in der Gruppe, um dein Menü zu öffnen.")

# Hauptfunktion zum Starten des Bots
def main():
    # Bot initialisieren
    app = Application.builder().token(TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))  # Start-Befehl registrieren
    app.add_handler(CommandHandler("konto", user_account))  # Benutzerkonto-Menü
    app.add_handler(CallbackQueryHandler(button_handler))  # Button-Klicks verarbeiten

    # Bot starten
    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()