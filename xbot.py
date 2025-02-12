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

# 📌 Registriert Nutzer, falls sie fehlen
def register_user_if_not_exists(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))

    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, chat_id, username, first_name, last_name, 0))
        conn.commit()
        print(f"✅ Neuer Nutzer gespeichert: {user_id} in Gruppe {chat_id}")
    conn.close()

# 📌 Holt ALLE Nutzer aus der Gruppe & registriert fehlende Nutzer
async def get_all_users_and_register(context: CallbackContext, chat_id):
    try:
        chat_members = await context.bot.get_chat(chat_id)
        conn = connect_db()
        cursor = conn.cursor()

        # ALLE Mitglieder holen und registrieren
        async for member in context.bot.get_chat_administrators(chat_id):
            user = member.user
            cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user.id, chat_id))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                               (user.id, chat_id, user.username, user.first_name, user.last_name, 0))
                print(f"✅ Neuer Nutzer registriert: {user.id} ({user.first_name}) in Gruppe {chat_id}")

        conn.commit()
        conn.close()
        print(f"✅ Alle Nutzer für Gruppe {chat_id} registriert.")

    except Exception as e:
        print(f"[ERROR] Fehler beim Abrufen der Nutzerliste: {e}")

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

    # Admin-Button NUR für Admins!
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Admin-Panel: Holt ALLE Nutzer & registriert fehlende Nutzer
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split("_")[1]

    print(f"[DEBUG] Admin-Panel geöffnet in Gruppe {chat_id}")

    await get_all_users_and_register(context, chat_id)

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ?", (chat_id,))
    users = cursor.fetchall()
    conn.close()

    if not users:
        await query.message.reply_text("⚠️ Keine Nutzer in der Datenbank gefunden!")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("🔹 Wähle einen Nutzer:", reply_markup=reply_markup)

# 📌 Hauptfunktion zum Starten des Bots
def main():
    initialize_database()  # Stellt sicher, dass die Datenbank existiert

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", user_account))  
    app.add_handler(CommandHandler("konto", user_account))  
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()