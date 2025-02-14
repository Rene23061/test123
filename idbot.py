import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS allowed_groups (chat_id INTEGER PRIMARY KEY, owner_id INTEGER)")
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Admins und Gruppen aus der Datenbank laden ---
def get_admins():
    cursor.execute("SELECT user_id FROM admins")
    return {row[0] for row in cursor.fetchall()}

def get_allowed_groups():
    cursor.execute("SELECT chat_id FROM allowed_groups")
    return {row[0] for row in cursor.fetchall()}

AUTHORIZED_USERS = get_admins()
AUTHORIZED_GROUPS = get_allowed_groups()

# --- Funktion zum Prüfen, ob Benutzer Admin ist ---
def is_admin(update: Update):
    return update.message.from_user.id in AUTHORIZED_USERS

# --- Funktion zum Prüfen, ob der Benutzer Gruppeninhaber ist ---
def is_group_owner(update: Update):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    cursor.execute("SELECT owner_id FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    return result and result[0] == user_id

# --- Funktion zum Prüfen, ob der Chat erlaubt ist ---
def is_group_allowed(update: Update):
    return update.message.chat_id in AUTHORIZED_GROUPS

# --- /start-Befehl ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    # Falls die Gruppe nicht erlaubt ist, prüfe, ob der Benutzer der Gruppeninhaber ist
    if chat_id not in AUTHORIZED_GROUPS:
        cursor.execute("INSERT OR IGNORE INTO allowed_groups (chat_id, owner_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()
        AUTHORIZED_GROUPS.add(chat_id)
        await update.message.reply_text("✅ Deine Gruppe wurde hinzugefügt! Du bist der Gruppeninhaber.")

    await show_bots(update, context)

# --- Admins verwalten ---
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🚫 Zugriff verweigert! Nur Admins dürfen neue Admins hinzufügen.")
        return

    try:
        new_admin_id = int(update.message.text.split()[-1])
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
        conn.commit()
        AUTHORIZED_USERS.add(new_admin_id)
        await update.message.reply_text(f"✅ Admin {new_admin_id} wurde hinzugefügt.")
    except ValueError:
        await update.message.reply_text("⚠️ Ungültige Eingabe! Verwende: /addadmin [Telegram-ID]")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🚫 Zugriff verweigert! Nur Admins dürfen Admins entfernen.")
        return

    try:
        remove_admin_id = int(update.message.text.split()[-1])
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (remove_admin_id,))
        conn.commit()
        AUTHORIZED_USERS.discard(remove_admin_id)
        await update.message.reply_text(f"✅ Admin {remove_admin_id} wurde entfernt.")
    except ValueError:
        await update.message.reply_text("⚠️ Ungültige Eingabe! Verwende: /removeadmin [Telegram-ID]")

# --- Gruppen verwalten (nur Admins oder Gruppeninhaber) ---
async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not (is_admin(update) or is_group_owner(update)):
        await update.message.reply_text("🚫 Zugriff verweigert! Nur Admins oder der Gruppeninhaber dürfen Gruppen entfernen.")
        return

    cursor.execute("DELETE FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    conn.commit()
    AUTHORIZED_GROUPS.discard(chat_id)
    await update.message.reply_text("✅ Die Gruppe wurde entfernt.")

# --- Alle Bots anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group_allowed(update):
        await update.message.reply_text("🚫 Zugriff verweigert! Deine Gruppe ist nicht autorisiert.")
        return

    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot starten ---
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("removegroup", remove_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))

    print("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()