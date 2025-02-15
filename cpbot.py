import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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

# --- Linkliste anzeigen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    logging.info(f"📋 Linkliste für Chat {chat_id} wird abgerufen...")

    # Datenbankabfrage für gespeicherte Links
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    # Debugging: Loggen, ob Links gefunden wurden
    if not links:
        logging.warning(f"❌ Keine Links in der Whitelist für Chat {chat_id} gefunden!")
        await query.message.edit_text("❌ Die Whitelist ist leer.")
        return

    # Debug: Liste aller gefundenen Links
    logging.debug(f"🔗 Gefundene Links für Chat {chat_id}: {links}")

    # Inline-Buttons zum Löschen von Links
    keyboard = [[InlineKeyboardButton(f"🗑 {link[0]}", callback_data=f"delete_{chat_id}_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"link_menu_{chat_id}")])

    try:
        await query.message.edit_text(
            "📋 **Whitelist:**\n" + "\n".join(f"- {link[0]}" for link in links),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        logging.info(f"✅ Linkliste erfolgreich gesendet für Chat {chat_id}.")
    except Exception as e:
        logging.error(f"❌ Fehler beim Anzeigen der Linkliste: {e}")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    link = "_".join(data[2:])  # Falls der Link `_` enthält, wird er korrekt rekonstruiert

    logging.info(f"🗑 Lösche Link {link} für Chat {chat_id}...")

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.answer(f"✅ {link} wurde gelöscht.", show_alert=True)
    logging.info(f"✅ Link {link} erfolgreich gelöscht.")
    await show_links(update, context)  # Aktualisiere die Liste

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle & Callback-Handler
    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(CallbackQueryHandler(show_links, pattern="show_links_"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="delete_"))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()