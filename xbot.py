import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

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

# 📌 Nutzer in der Datenbank speichern (mit Gruppen-ID)
def save_user(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute(
            "INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, 0)",
            (user_id, chat_id, username, first_name, last_name)
        )
        conn.commit()
        print(f"✅ Neuer Nutzer {first_name} ({user_id}) in Gruppe {chat_id} gespeichert!")
    else:
        print(f"ℹ️ Nutzer {first_name} ({user_id}) in Gruppe {chat_id} bereits vorhanden.")

    conn.close()

# 📌 Holt ALLE Nutzer aus einer bestimmten Gruppe
def get_all_users(chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    print(f"🔍 {len(users)} Nutzer in Gruppe {chat_id} gefunden")
    return users

# 📌 Admin-Check (Sichtbarkeit von Admin-Menüs)
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        print(f"[DEBUG] Admin-Check für {user_id} in Chat {chat_id} - Status: {chat_member.status}")
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Fehler bei Admin-Check für {user_id} in Chat {chat_id}: {e}")
        return False

# 📌 Benutzerkonto-Menü im Privat-Chat anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.message.chat_id  # Richtige Gruppen-ID holen
    private_chat_id = user.id

    # 📌 Nutzer zur Datenbank hinzufügen (falls nicht vorhanden)
    save_user(user.id, chat_id, user.username, user.first_name, user.last_name)

    is_admin_user = await is_admin(context, user.id, chat_id)

    print(f"[DEBUG] /konto aufgerufen von {user.id} in Chat {chat_id}, Admin: {is_admin_user}")

    welcome_text = f"👤 Benutzerkonto für {user.first_name}\n📌 **Gruppe:** `{chat_id}`\nHier kannst du dein Guthaben verwalten."

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user.id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        print(f"[DEBUG] ✅ Admin-Button für {user.id} sichtbar.")
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Admin-Panel zeigt die Nutzer der richtigen Gruppe an
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        print(f"[ERROR] Ungültige Callback-Daten erhalten: {data}")
        await query.answer("⚠ Fehler: Gruppen-ID konnte nicht erkannt werden.", show_alert=True)
        return

    chat_id = int(data[2])  # Holt Gruppen-ID aus Callback-Daten
    print(f"[DEBUG] 🔍 Admin-Panel geöffnet für Gruppe {chat_id}")

    users = get_all_users(chat_id)

    if not users:
        await query.message.edit_text("⚠️ Keine Nutzer in der Datenbank gefunden!")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_back_{chat_id}")])  # Zurück-Button

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🔹 Wähle einen Nutzer für Guthaben-Verwaltung:", reply_markup=reply_markup)

# 📌 Zurück zum Hauptmenü für Admins
async def admin_back(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        print(f"[ERROR] Ungültige Zurück-Callback-Daten: {data}")
        await query.answer("⚠ Fehler: Gruppen-ID nicht erkannt.", show_alert=True)
        return

    chat_id = int(data[2])
    print(f"[INFO] 🔙 Zurück zum Hauptmenü in Gruppe {chat_id}")

    is_admin_user = await is_admin(context, query.from_user.id, chat_id)

    welcome_text = f"👤 Benutzerkonto für {query.from_user.first_name}\n📌 **Gruppe:** `{chat_id}`\nHier kannst du dein Guthaben verwalten."

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{query.from_user.id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Hauptfunktion zum Starten des Bots
def main():
    initialize_database()  # Stellt sicher, dass die Datenbank existiert

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", user_account))  
    app.add_handler(CommandHandler("konto", user_account))  
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))  
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back_"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()