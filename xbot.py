import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

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

# 📌 Nutzer speichern (falls nicht vorhanden)
def save_user(user_id, chat_id, username, first_name, last_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, 0)",
                       (user_id, chat_id, username, first_name, last_name))
        conn.commit()
        print(f"✅ Neuer Nutzer {first_name} ({user_id}) in Gruppe {chat_id} gespeichert!")
    else:
        print(f"ℹ️ Nutzer {first_name} ({user_id}) in Gruppe {chat_id} bereits vorhanden.")

    conn.close()

# 📌 Holt alle Nutzer für eine Gruppe (mit Paginierung)
def get_users_by_page(chat_id, page=0, limit=20):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name FROM users WHERE chat_id = ? LIMIT ? OFFSET ?", 
                   (chat_id, limit, page * limit))
    users = cursor.fetchall()
    conn.close()
    print(f"🔍 {len(users)} Nutzer in Gruppe {chat_id} (Seite {page}) gefunden")
    return users

# 📌 Admin-Check
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Admin-Check für {user_id} fehlgeschlagen: {e}")
        return False

# 📌 Benutzerkonto-Menü im Privat-Chat anzeigen
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

# 📌 Admin-Panel mit Nutzerliste (20 Nutzer pro Seite)
async def admin_manage(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        await query.answer("⚠ Fehler: Gruppen-ID konnte nicht erkannt werden.", show_alert=True)
        return

    chat_id = int(data[2])
    page = int(data[3]) if len(data) > 3 else 0

    users = get_users_by_page(chat_id, page)

    keyboard = [[InlineKeyboardButton(f"{user[1] or user[2]}", callback_data=f"user_select_{user[0]}_{chat_id}")]
                for user in users]

    if page > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"admin_manage_{chat_id}_{page - 1}")])

    keyboard.append([InlineKeyboardButton("➡️ Weiter", callback_data=f"admin_manage_{chat_id}_{page + 1}")])
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_back_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔹 Wähle einen Nutzer für Guthaben-Verwaltung:", reply_markup=reply_markup)

# 📌 Nutzerverwaltung
async def user_select(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[1].lstrip('-').isdigit() or not data[2].lstrip('-').isdigit():
        await query.answer("⚠ Fehler: Nutzer-ID konnte nicht erkannt werden.", show_alert=True)
        return

    user_id = int(data[1])
    chat_id = int(data[2])

    keyboard = [
        [InlineKeyboardButton("💰 Guthaben anzeigen", callback_data=f"show_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➕ Guthaben hinzufügen", callback_data=f"add_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("➖ Guthaben entfernen", callback_data=f"remove_balance_{user_id}_{chat_id}")],
        [InlineKeyboardButton("🔙 Zurück", callback_data=f"admin_manage_{chat_id}_0")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"💰 Wähle eine Aktion für den Nutzer {user_id}:", reply_markup=reply_markup)

# 📌 Zurück zum Hauptmenü
async def admin_back(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")

    if len(data) < 3 or not data[2].lstrip('-').isdigit():
        await query.answer("⚠ Fehler: Gruppen-ID nicht erkannt.", show_alert=True)
        return

    chat_id = int(data[2])

    is_admin_user = await is_admin(context, query.from_user.id, chat_id)

    welcome_text = f"👤 Benutzerkonto für {query.from_user.first_name}\n📌 **Gruppe:** `{chat_id}`\nHier kannst du dein Guthaben verwalten."

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{query.from_user.id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data="show_purchases")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data="top_up")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data="settings")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}_0")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# 📌 Bot starten
def main():
    initialize_database()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("konto", user_account))
    app.add_handler(CallbackQueryHandler(admin_manage, pattern="^admin_manage_"))
    app.add_handler(CallbackQueryHandler(user_select, pattern="^user_select_"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back_"))

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()