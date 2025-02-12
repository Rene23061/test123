import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
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
    cursor.execute("SELECT id FROM users WHERE id = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, chat_id, username, first_name, last_name, coins) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, chat_id, username, first_name, last_name, 0))
        conn.commit()
    conn.close()

# Prüft, ob der Nutzer Admin oder Gruppeninhaber ist (Fix: Immer richtige Gruppen-ID verwenden)
async def is_admin(context: CallbackContext, user_id, chat_id):
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        print(f"[DEBUG] Admin-Check für {user_id} in Chat {chat_id} - Status: {chat_member.status}")
        return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"[ERROR] Fehler bei Admin-Check für {user_id} in Chat {chat_id}: {e}")
        return False

# Benutzerkonto-Menü im Privat-Chat anzeigen
async def user_account(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Speichert die Gruppen-ID
    private_chat_id = user.id

    print(f"[DEBUG] /konto von {user.id} in Chat {chat_id}")

    if user.is_bot:
        print(f"[DEBUG] {user.id} ist ein Bot und wird ignoriert.")
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    is_admin_user = await is_admin(context, user.id, chat_id)

    print(f"[DEBUG] Benutzer: {user.id}, Admin-Status: {is_admin_user}")

    welcome_text = (
        f"👤 Benutzerkonto für {user.first_name}\n"
        f"📌 Gruppe: {chat_id}\n"
        "Hier kannst du dein Guthaben verwalten.\n"
        "Wähle eine Option:"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Guthaben anzeigen", callback_data=f"show_balance_{chat_id}")],
        [InlineKeyboardButton("📜 Meine Käufe", callback_data=f"show_purchases_{chat_id}")],
        [InlineKeyboardButton("💳 Guthaben aufladen", callback_data=f"top_up_{chat_id}")],
        [InlineKeyboardButton("🛠 Einstellungen", callback_data=f"settings_{chat_id}")]
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Guthaben verwalten", callback_data=f"admin_manage_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=private_chat_id, text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# /konto wird automatisch zum Privat-Chat geleitet
async def konto_redirect(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id  # Speichert die Gruppen-ID

    print(f"[DEBUG] /konto aufgerufen von {user.id} in Chat {chat_id}")

    if user.is_bot:
        print(f"[DEBUG] {user.id} ist ein Bot und wird ignoriert.")
        return  

    register_user_if_not_exists(user.id, chat_id, user.username, user.first_name, user.last_name)
    await user_account(update, context)

# Admin-Panel öffnen (Fix: Korrekte Gruppen-ID übergeben)
async def admin_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    # Gruppen-ID aus Callback-Data holen, damit der Admin-Check die richtige Gruppe verwendet
    data = query.data.split("_")
    try:
        chat_id = int(data[1]) if len(data) > 1 and data[1].startswith("-") else query.message.chat_id
    except Exception:
        chat_id = query.message.chat_id

    print(f"[DEBUG] Admin-Panel von {user.id} in Chat {chat_id} angefordert")

    is_admin_user = await is_admin(context, user.id, chat_id)

    print(f"[DEBUG] Admin-Check für {user.id} in Chat {chat_id}, Admin-Status: {is_admin_user}")

    if not is_admin_user:
        await context.bot.send_message(chat_id=user.id, text="⛔ Du bist kein Admin!")
        return

    await context.bot.send_message(chat_id=user.id, text=f"⚙️ Admin-Panel für Gruppe {chat_id} geöffnet!")

# Hauptfunktion zum Starten des Bots
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", konto_redirect))  
    app.add_handler(CommandHandler("konto", konto_redirect))  
    app.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin_manage_"))  

    print("✅ Bot erfolgreich gestartet!")
    app.run_polling()

if __name__ == '__main__':
    main()