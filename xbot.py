import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Bot-Token
TOKEN = "DEIN_BOT_TOKEN_HIER"

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

# 📌 Nutzer in der Datenbank speichern
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

# 📌 Holt Nutzer aus einer bestimmten Gruppe mit Pagination
def get_users_paginated(chat_id, page=0, page_size=20):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ? LIMIT ? OFFSET ?", 
                   (chat_id, page_size, page * page_size))
    users = cursor.fetchall()
    conn.close()
    return users

# 📌 Admin-Check
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Fehler bei Admin-Check für {user_id} in Chat {chat_id}: {e}")
        return False

# 📌 Benutzerkonto-Menü
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.message.chat_id
    private_chat_id = user.id

    save_user(user.id, chat_id, user.username, user.first_name, user.last_name)

    is_admin_user = await is_admin(context, user.id, chat_id)

    welcome_text = f"👤 Benutzerkonto für {user.first_name}\n📌 **Gruppe:** `{chat_id}`\nHier kannst du dein Guthaben verwalten."

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{user.id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}_0")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Admin-Panel mit Pagination
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 4:
        await query.answer("⚠ Fehler: Ungültige Daten!", show_alert=True)
        return

    chat_id = int(data[2])
    page = int(data[3])

    users = get_users_paginated(chat_id, page)

    if not users:
        await query.answer("⚠ Keine Nutzer gefunden!", show_alert=True)
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]

    if page > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"admin_manage_{chat_id}_{page - 1}")])
    if len(users) == 20:
        keyboard.append([InlineKeyboardButton("➡️ Weiter", callback_data=f"admin_manage_{chat_id}_{page + 1}")])

    keyboard.append([InlineKeyboardButton("🔍 Nutzer suchen", callback_data=f"admin_search_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_back_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🔹 Wähle einen Nutzer:", reply_markup=reply_markup)

# 📌 Nutzer-Suche
async def admin_search(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split("_")[2]
    
    await query.message.edit_text("🔍 Bitte gib den Namen oder die ID des Nutzers ein:")
    context.user_data["search_chat_id"] = chat_id  # Speichert die Gruppen-ID für spätere Suche

# 📌 Suchergebnis anzeigen
async def process_search(update: Update, context: CallbackContext):
    chat_id = context.user_data.get("search_chat_id")
    search_query = update.message.text

    if not chat_id:
        await update.message.reply_text("⚠ Kein Gruppen-Kontext gefunden!")
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ? AND (username LIKE ? OR first_name LIKE ? OR id LIKE ?)", 
                   (chat_id, f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    users = cursor.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text("⚠ Kein Nutzer gefunden!")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"admin_user_{user[0]}_{chat_id}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🔹 Wähle einen Nutzer:", reply_markup=reply_markup)

# 📌 Zurück zum Hauptmenü
async def admin_back(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[2])

    welcome_text = f"👤 Benutzerkonto\n📌 **Gruppe:** `{chat_id}`\nHier kannst du dein Guthaben verwalten."

    keyboard = [[InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}_0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Bot starten
def main():
    initialize_database()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("konto", user_account))
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))
    app.add_handler(CallbackQueryHandler(admin_search, pattern="^admin_search_"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_search))

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()