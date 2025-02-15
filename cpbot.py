import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Prüft, ob ein Link in der Whitelist ist ---
def is_whitelisted(chat_id, link):
    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    return cursor.fetchone() is not None

# --- Befehl: /link (Öffnet das Menü zur Linkverwaltung) ---
async def link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Link anzeigen/löschen", callback_data=f"show_links_{chat_id}")]
    ]
    await update.message.reply_text("🔗 **Link-Verwaltung:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link hinzufügen: Fragt den Benutzer nach einem Link ---
async def add_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    await query.message.edit_text("✏️ Bitte sende mir den **Link**, den du zur Whitelist hinzufügen möchtest.")
    context.user_data["waiting_for_link"] = chat_id  # Speichert, dass ein Link erwartet wird

# --- Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")
    if not chat_id:
        return

    link = update.message.text.strip()
    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("⚠️ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
        return

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()
        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")

    context.user_data.pop("waiting_for_link", None)

# --- Whitelist anzeigen ---
async def show_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Keine Links in der Whitelist.")
        return

    link_list = "\n".join(f"- {link[0]}" for link in links)
    keyboard = [[InlineKeyboardButton("🗑 Link löschen", callback_data=f"delete_menu_{chat_id}")]]

    await query.message.edit_text(f"📋 **Whitelist:**\n{link_list}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link-Löschmenü ---
async def delete_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Keine Links zum Löschen.")
        return

    keyboard = [[InlineKeyboardButton(f"❌ {link[0]}", callback_data=f"confirm_delete_{chat_id}_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"show_links_{chat_id}")])

    await query.message.edit_text("🔍 **Wähle einen Link zum Löschen:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Sicherheitsabfrage zum Löschen ---
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = data[2]
    link = "_".join(data[3:])  # Falls der Link Unterstriche enthält

    keyboard = [
        [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_{chat_id}_{link}")],
        [InlineKeyboardButton("❌ Nein, abbrechen", callback_data=f"delete_menu_{chat_id}")]
    ]

    await query.message.edit_text(f"⚠️ **Bist du sicher, dass du diesen Link löschen möchtest?**\n\n🔗 {link}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = data[1]
    link = "_".join(data[2:])

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.answer(f"✅ {link} wurde gelöscht.", show_alert=True)
    await delete_link_menu(update, context)

# --- Nachrichtenkontrolle ---
async def kontrolliere_nachricht(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    user = message.from_user
    text = message.text or ""

    # Nach Telegram-Gruppenlinks suchen
    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        link = match.group(0)

        # Wenn der Link nicht in der Whitelist steht, Nachricht löschen
        if not is_whitelisted(chat_id, link):
            await message.reply_text(f"🚫 Dein Link wurde gelöscht: {link}")
            await message.delete()
            return

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("link", link_menu))
    application.add_handler(CallbackQueryHandler(add_link_prompt, pattern="add_link_"))
    application.add_handler(CallbackQueryHandler(show_links, pattern="show_links_"))
    application.add_handler(CallbackQueryHandler(delete_link_menu, pattern="delete_menu_"))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern="confirm_delete_"))
    application.add_handler(CallbackQueryHandler(delete_link, pattern="delete_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_link))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, kontrolliere_nachricht))

    print("🤖 Anti-Gruppenlink-Bot gestartet...")
    application.run_polling()

if __name__ == "__main__":
    main()