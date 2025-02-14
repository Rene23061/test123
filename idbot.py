import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = init_db()

# --- /start-Befehl ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Willkommen! Wähle einen Bot zur Verwaltung:")
    await show_bots(update, context)

# ===================== Bot-Auswahl =====================

async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else update.message
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.reply_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(query, Update) or not hasattr(query, "edit_message_text"):
        await query.reply_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=reply_markup)

async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "")
    context.user_data["selected_bot"] = bot_name  

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("➖ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_bots")]
    ]
    
    await query.edit_message_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===================== Gruppe Entfernen (Fix) =====================

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✍️ Sende die Gruppen-ID, die du entfernen möchtest.")
    context.user_data["awaiting_group_remove"] = True

async def process_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_group_remove"):
        bot_name = context.user_data["selected_bot"]
        chat_id = update.message.text.strip()
        column_name = f"allow_{bot_name}"

        # 🛠 Debug: Zeigt an, welche ID gelöscht werden soll
        print(f"🔍 Lösche Gruppe: {chat_id} für {bot_name}")

        # Überprüfen, ob die Gruppe existiert
        cursor.execute(f"SELECT chat_id FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
        exists = cursor.fetchone()

        if not exists:
            await update.message.reply_text(f"⚠️ Die Gruppe {chat_id} existiert nicht für {bot_name}.")
            print(f"⚠️ Gruppe {chat_id} existiert nicht.")
        else:
            # 🛠 Debug: Bestätigung, dass Gruppe gefunden wurde
            print(f"✅ Gruppe {chat_id} existiert. Lösche jetzt...")
            
            cursor.execute(f"DELETE FROM allowed_groups WHERE chat_id = ? AND {column_name} = 1", (chat_id,))
            conn.commit()

            if cursor.rowcount > 0:
                await update.message.reply_text(f"✅ Gruppe {chat_id} wurde erfolgreich entfernt.")
                print(f"✅ Gruppe {chat_id} wurde erfolgreich entfernt.")
            else:
                await update.message.reply_text(f"❌ Fehler beim Löschen von {chat_id}.")
                print(f"❌ Fehler beim Löschen von {chat_id}.")

        context.user_data["awaiting_group_remove"] = False
        await manage_bot(update, context)  # Zurück ins Bot-Management-Menü

# ===================== Bot Initialisierung =====================

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    
    # Gruppen Einfügen und Entfernen als eigene MessageHandler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_group))

    # Callback-Handler für Menüführung
    application.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()