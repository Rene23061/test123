import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Logging für NUR Datenbank-Fehler ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Deaktiviert HTTP-Logs
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

# --- DEBUG-Funktion: Erzwingt das Schreiben in die Log-Datei ---
def debug_log(message):
    try:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"{message}\n")
    except Exception as e:
        print(f"❌ KANN NICHT SCHREIBEN: {e}")

# 🔍 **TEST: Prüfen, ob Logs geschrieben werden können**
try:
    with open("debug_log.txt", "a") as debug_file:
        debug_file.write("🔍 DEBUG-TEST: Log-Datei wurde erfolgreich geöffnet!\n")
except Exception as e:
    print(f"❌ KANN NICHT SCHREIBEN: {e}")

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Bitte gib das Passwort ein, um fortzufahren:")
    context.user_data["awaiting_password"] = True

# --- Passwortprüfung ---
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == PASSWORD:
            await update.message.reply_text("✅ Passwort korrekt! Zugriff gewährt.")
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
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

    if update.callback_query:
        await update.callback_query.edit_message_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

# --- Gruppe zur Whitelist hinzufügen ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✍️ Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

# --- TEST: Prüfen, ob `process_add_group()` AUFGERUFEN WIRD ---
async def process_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.text.strip()
    bot_name = context.user_data.get("selected_bot")
    column_name = f"allow_{bot_name}"

    debug_log(f"🔍 process_add_group() gestartet: {chat_id} → {column_name}")
    await update.message.reply_text(f"✅ TEST: `process_add_group()` wurde AUFGERUFEN mit ID {chat_id}")

    if not bot_name:
        await update.message.reply_text("⚠️ Fehler: Kein Bot ausgewählt!")
        return

    try:
        cursor.execute(f"UPDATE allowed_groups SET {column_name} = 1 WHERE chat_id = ?", (chat_id,))
        rows_updated = cursor.rowcount  

        if rows_updated == 0:
            cursor.execute(f"INSERT INTO allowed_groups (chat_id, {column_name}) VALUES (?, 1)", (chat_id,))
            debug_log(f"✅ INSERT erfolgreich für {chat_id} in {column_name}")

        conn.commit()

        cursor.execute(f"SELECT * FROM allowed_groups WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        debug_log(f"📌 Nach Einfügen: {row}")

        await update.message.reply_text(f"✅ Gruppe {chat_id} wurde dem Bot {bot_name} hinzugefügt.")

    except sqlite3.Error as e:
        debug_log(f"❌ SQL-Fehler: {e}")
        await update.message.reply_text(f"⚠️ SQL-Fehler: {e}")

    context.user_data["awaiting_group_add"] = False

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_group))

    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()