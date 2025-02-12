import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

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

# 📌 Holt Guthaben eines Nutzers
def get_balance(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# 📌 Holt ALLE Nutzer aus einer bestimmten Gruppe
def get_all_users(chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    print(f"🔍 {len(users)} Nutzer in Gruppe {chat_id} gefunden")
    return users

# 📌 Admin-Panel: Guthaben-Verwaltung für einen Nutzer
async def admin_user_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        await query.answer("⚠ Fehler: Ungültige Daten.", show_alert=True)
        return

    user_id = int(data[2])
    chat_id = int(data[3])
    balance = get_balance(user_id)

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"admin_show_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"admin_add_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➖ Guthaben entfernen", callback_data=f"admin_remove_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_manage_{chat_id}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"💰 Guthaben-Verwaltung für Benutzer {user_id}\n📌 Aktuelles Guthaben: {balance} Coins", reply_markup=reply_markup)

# 📌 Zeigt Guthaben eines Nutzers an
async def admin_show_balance(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        await query.answer("⚠ Fehler: Ungültige Daten.", show_alert=True)
        return

    user_id = int(data[2])
    chat_id = int(data[3])
    balance = get_balance(user_id)

    await query.answer(f"💰 Guthaben von Benutzer {user_id}: {balance} Coins", show_alert=True)

# 📌 Hauptfunktion zum Starten des Bots
def main():
    initialize_database()  

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", user_account))  
    app.add_handler(CommandHandler("konto", user_account))  
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))  
    app.add_handler(CallbackQueryHandler(admin_user_actions, pattern="^admin_user_"))  
    app.add_handler(CallbackQueryHandler(admin_show_balance, pattern="^admin_show_balance_"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()