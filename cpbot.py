import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Regulärer Ausdruck für Telegram-Gruppenlinks ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/(joinchat|[+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT UNIQUE
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- /link Befehl: Inline-Menü zum Hinzufügen eines Links ---
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📎 Link hinzufügen", callback_data="add_link")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Möchtest du einen Link zur Whitelist hinzufügen?", reply_markup=reply_markup)

# --- Callback: Link-Eingabe aktivieren ---
async def add_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Bitte sende den Link, den du zur Whitelist hinzufügen möchtest.")
    context.user_data["adding_link"] = True  # Status für die Link-Eingabe setzen

# --- Nachrichtenhandler: Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "adding_link" in context.user_data and context.user_data["adding_link"]:
        chat_id = update.message.chat_id
        link = update.message.text.strip()

        cursor.execute("INSERT OR IGNORE INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()

        keyboard = [
            [InlineKeyboardButton("➕ Weiteren Link hinzufügen", callback_data="add_link")],
            [InlineKeyboardButton("❌ Schließen", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f"✅ Link gespeichert: {link}", reply_markup=reply_markup)
        context.user_data["adding_link"] = False

# --- /list Befehl: Alle Links anzeigen ---
async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        keyboard = [[InlineKeyboardButton(link[0], url=link[0])] for link in links]
        keyboard.append([InlineKeyboardButton("❌ Schließen", callback_data="close")])  # Schließen-Button hinzufügen
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 **Whitelist dieser Gruppe:**", reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Die Whitelist dieser Gruppe ist leer.")

# --- /del Befehl: Menü mit allen gespeicherten Links anzeigen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if links:
        keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_{link[0]}")] for link in links]
        keyboard.append([InlineKeyboardButton("❌ Schließen", callback_data="close")])  # Schließen-Button hinzufügen
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Wähle einen Link zum Löschen:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Es gibt keine gespeicherten Links.")

# --- Callback: Sicherheitsabfrage zum Löschen ---
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    link = query.data.replace("delete_", "")

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"confirm_delete_{link}")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(f"Bist du sicher, dass du den Link löschen möchtest?\n{link}", reply_markup=reply_markup)

# --- Callback: Link endgültig löschen ---
async def delete_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    link = query.data.replace("confirm_delete_", "")
    chat_id = query.message.chat_id

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("🗑 Weiteren Link löschen", callback_data="del")],
        [InlineKeyboardButton("❌ Schließen", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(f"✅ Der Link wurde gelöscht: {link}", reply_markup=reply_markup)

# --- Callback: Schließen ---
async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle hinzufügen
    application.add_handler(CommandHandler("link", add_link))
    application.add_handler(CommandHandler("list", list_links))
    application.add_handler(CommandHandler("del", delete_link))

    # Callback-Handler für Inline-Tastaturen
    application.add_handler(CallbackQueryHandler(add_link_callback, pattern="^add_link$"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="^del$"))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(delete_confirmed, pattern="^confirm_delete_"))
    application.add_handler(CallbackQueryHandler(close, pattern="^close$"))

    # Nachrichten-Handler für Link-Eingabe
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))

    print("🤖 Bot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()