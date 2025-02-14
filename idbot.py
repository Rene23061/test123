import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Logging für Debugging (nur Datenbank-Fehler) ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # HTTP-Logs deaktivieren
logging.getLogger("telegram").setLevel(logging.WARNING)

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort ---
PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = init_db()

# --- DEBUG-Log-Funktion ---
def debug_log(message):
    try:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"{message}\n")
    except Exception as e:
        print(f"❌ KANN NICHT SCHREIBEN: {e}")

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug_log("🔐 /start wurde aufgerufen.")
    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um fortzufahren:")
    context.user_data["awaiting_password"] = True

# --- Passwortprüfung (nur nach /start) ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_password"):
        return  # Ignoriert andere Eingaben

    debug_log(f"🔑 Passwortprüfung gestartet mit Eingabe: {update.message.text}")

    if update.message.text == PASSWORD:
        await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.")
        context.user_data["authenticated"] = True
        context.user_data["awaiting_password"] = False
        context.user_data.pop("awaiting_password", None)  # **Passwortprüfung deaktivieren**
        await show_bots(update, context)  
    else:
        await update.message.reply_text("❌ Falsches Passwort! Zugriff verweigert.")
        context.user_data["awaiting_password"] = False

# --- Alle Bots aus der Datenbank anzeigen ---
async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug_log("📌 show_bots() wurde aufgerufen.")

    if not context.user_data.get("authenticated"):
        await update.message.reply_text("🚫 Zugriff verweigert! Bitte starte mit /start und gib das richtige Passwort ein.")
        return

    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    debug_log(f"📌 Gefundene Bots: {bots}")

    if not bots:
        await update.message.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Bot-Verwaltungsmenü nach Auswahl eines Bots ---
async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "")
    context.user_data["selected_bot"] = bot_name  

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_bots")]
    ]
    
    await query.message.edit_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Gruppe zur Whitelist hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    debug_log("🔍 add_group() wurde aufgerufen.")
    await query.message.edit_text("✍️ Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

# --- Gruppenanzeige Fix ---
async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name}"

    cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    if groups:
        response = f"📋 **Erlaubte Gruppen für {bot_name}:**\n" + "\n".join(f"- `{group[0]}`" for group in groups)
    else:
        response = f"❌ Keine Gruppen für {bot_name} eingetragen."

    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Zurück", callback_data="manage_bot_" + bot_name)]
    ]))

# --- FIX: Gruppen-ID Verarbeitung ---
async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_group_add"):
        return  # Ignoriert falsche Eingaben

    chat_id = update.message.text.strip()

    # **Sicherstellen, dass es eine numerische ID ist**
    if not chat_id.lstrip('-').isdigit():
        await update.message.reply_text("⚠️ Fehler: Ungültige Gruppen-ID!")
        return

    chat_id = int(chat_id)
    bot_name = context.user_data.get("selected_bot")
    column_name = f"allow_{bot_name}"

    debug_log(f"📌 Eintragen: {chat_id} → {column_name}")

    if not bot_name:
        await update.message.reply_text("⚠️ Fehler: Kein Bot ausgewählt!")
        debug_log("❌ Fehler: Kein Bot ausgewählt!")
        return

    try:
        cursor.execute(f"INSERT OR IGNORE INTO allowed_groups (chat_id) VALUES (?)", (chat_id,))
        cursor.execute(f"UPDATE allowed_groups SET {column_name} = 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()

        cursor.execute(f"SELECT * FROM allowed_groups WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        debug_log(f"✅ Nach Einfügen: {row}")

        await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")

    except sqlite3.Error as e:
        debug_log(f"❌ SQL-Fehler: {e}")
        await update.message.reply_text(f"⚠️ SQL-Fehler: {e}")

    context.user_data["awaiting_group_add"] = False

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    
    # **FIXED: Passwort-Filter nur nach /start aktiv**
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{PASSWORD}$"), check_password))  

    # **Gruppen-ID-Filter nur wenn erwartet**
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^-?[0-9]+$"), process_add_group))  

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))

    debug_log("🚀 Bot wurde gestartet!")
    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()