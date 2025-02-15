import re
import sqlite3
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

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

# --- Menü mit Schließen-Button ---
async def link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    logging.info(f"📌 /link wurde empfangen in Chat {chat_id}")

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{chat_id}")],
        [InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")]
    ]

    await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    logging.debug("✅ Menü erfolgreich gesendet.")

# --- Menü schließen ---
async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()
    await query.answer()

# --- Link-Liste abrufen (Fix für Fehler) ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    logging.info(f"📋 Link-Liste wird für Chat {chat_id} abgerufen...")

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Die Whitelist ist leer.")
        return

    keyboard = [[InlineKeyboardButton(link[0], callback_data=f"delete_link_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("❌ Menü schließen", callback_data="close_menu")])

    await query.message.edit_text("📋 **Whitelist:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    logging.debug("✅ Link-Liste erfolgreich gesendet.")

# --- Link löschen (Fix für Fehler) ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    link = query.data.replace("delete_link_", "")
    chat_id = query.message.chat_id

    logging.info(f"🗑️ Löschvorgang gestartet für {link} in Chat {chat_id}")

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.message.edit_text(f"✅ **{link}** wurde erfolgreich gelöscht.")
    logging.debug("✅ Link erfolgreich aus der Whitelist entfernt.")

# --- Link hinzufügen: Benutzer sendet einen Link ---
async def add_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    logging.info(f"📌 Link-Hinzufügen gestartet in Chat {chat_id}")

    context.user_data["waiting_for_link"] = chat_id  # Status speichern
    logging.debug(f"📝 `waiting_for_link` gesetzt auf {chat_id}")

    await query.message.edit_text("✏️ Bitte sende mir den **Link**, den du zur Whitelist hinzufügen möchtest.")

# --- Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")

    if not chat_id:
        logging.error("❌ `waiting_for_link` ist `None`. Der Bot speichert nichts!")
        await update.message.reply_text("⚠️ Fehler: Keine Gruppe erkannt. Bitte starte /link erneut.")
        return

    link = update.message.text.strip()
    logging.info(f"📩 Eingetragener Link: {link}")

    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("⚠️ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
        return

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        logging.info(f"✅ Link erfolgreich gespeichert: {link}")

        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
        context.user_data.pop("waiting_for_link", None)  # Status löschen

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")

# --- Nachrichtenkontrolle & Link-Löschung (Fix für Menü-Fehler) ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if not message or not message.text:
        return

    user = message.from_user
    text = message.text.strip()

    if context.user_data.get("waiting_for_link") == chat_id:
        logging.info(f"✋ Nachricht wird NICHT gelöscht, da der Bot auf einen Link wartet.")
        return

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)
        logging.info(f"🔗 Erkannter Link in Nachricht: {link}")

        if not is_whitelisted(chat_id, link):
            logging.warning(f"🚨 Unerlaubter Link erkannt! Lösche Nachricht von {user.full_name}: {link}")
            try:
                await message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {user.full_name}, dein Link wurde gelöscht!\n❌ Nicht erlaubter Link: {link}",
                    reply_to_message_id=message.message_id
                )
            except Exception as e:
                logging.error(f"⚠️ Fehler beim Löschen der Nachricht: {e}")

# --- Prüfen, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    logging.debug(f"🔍 Prüfe, ob {link} in der Whitelist von {chat_id} ist...")
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    result = cursor.fetchone()
    logging.debug(f"📋 Whitelist-Check Ergebnis: {result}")
    return result is not None

# --- Hauptfunktion zum Starten des Bots ---
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(CallbackQueryHandler(add_link_prompt, pattern="add_link_"))
    application.add_handler(CallbackQueryHandler(show_links, pattern="show_links_"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="delete_link_"))
    application.add_handler(CallbackQueryHandler(close_menu, pattern="close_menu"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(TELEGRAM_LINK_PATTERN), kontrolliere_nachricht))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()