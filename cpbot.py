import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "8012589725:AAEO5PdbLQiW6nwIRHmB6AayXMO7f31ukvc"

# --- Logging aktivieren ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)

# --- Regulärer Ausdruck für Telegram-Links ---
TELEGRAM_LINK_PATTERN = re.compile(r"(https?://)?(t\.me|telegram\.me)/([+a-zA-Z0-9_/]+)")

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("/root/cpkiller/whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüfen, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    result = cursor.fetchone()
    return result is not None

# --- Befehl: /link (Öffnet das Menü zur Linkverwaltung) ---
async def link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    logging.info(f"📌 /link wurde empfangen in Chat {chat_id}")

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{chat_id}")]
    ]

    await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    logging.debug("✅ Menü erfolgreich gesendet.")

# --- Link hinzufügen ---
async def add_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    logging.info(f"📌 Link-Hinzufügen gestartet in Chat {chat_id}")

    await query.message.edit_text("✏️ Bitte sende mir den **Link**, den du zur Whitelist hinzufügen möchtest.")
    context.user_data["waiting_for_link"] = chat_id

# --- Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")
    if not chat_id:
        logging.warning("⚠️ Kein Chat für Link-Speicherung erkannt. Abbruch.")
        return

    link = update.message.text.strip()
    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("⚠️ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
        return

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
        logging.info(f"✅ Link erfolgreich gespeichert: {link}")
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")

    context.user_data.pop("waiting_for_link", None)

# --- Linkliste anzeigen & Löschen ermöglichen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    logging.info(f"📋 Linkliste für Chat {chat_id} wird abgerufen...")

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Die Whitelist ist leer.")
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {link[0]}", callback_data=f"delete_{chat_id}_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"link_menu_{chat_id}")])

    await query.message.edit_text("📋 **Whitelist:**\n" + "\n".join(f"- {link[0]}" for link in links),
                                  reply_markup=InlineKeyboardMarkup(keyboard),
                                  parse_mode="Markdown")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    link = "_".join(data[2:])

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.answer(f"✅ {link} wurde gelöscht.", show_alert=True)
    await show_links(update, context)  # Aktualisiere die Liste

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle & Callback-Handler
    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(CallbackQueryHandler(add_link_prompt, pattern="add_link_"))
    application.add_handler(CallbackQueryHandler(show_links, pattern="show_links_"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="delete_"))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()