import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall()]
    if "group_name" not in columns:
        cursor.execute("ALTER TABLE allowed_groups ADD COLUMN group_name TEXT;")
        conn.commit()

    return conn, cursor

conn, cursor = init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Willkommen! Wähle eine Aktion:", reply_markup=main_menu())

def main_menu():
    keyboard = [[InlineKeyboardButton("🔧 Bot verwalten", callback_data="show_bots")]]
    return InlineKeyboardMarkup(keyboard)

async def show_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cursor.execute("PRAGMA table_info(allowed_groups);")
    columns = [col[1] for col in cursor.fetchall() if col[1].startswith("allow_")]

    bots = [col.replace("allow_", "") for col in columns]
    if not bots:
        await query.message.edit_text("❌ Keine Bots gefunden!")
        return

    keyboard = [[InlineKeyboardButton(bot, callback_data=f"manage_bot_{bot}")] for bot in bots]
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")])
    
    await query.message.edit_text("🤖 Wähle einen Bot zur Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = query.data.replace("manage_bot_", "").lower()
    context.user_data["selected_bot"] = bot_name  

    keyboard = [
        [InlineKeyboardButton("➕ Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("➖ Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("📋 Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="show_bots")]
    ]
    
    await query.message.edit_text(f"⚙️ Verwaltung für {bot_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name.lower()}"

    cursor.execute(f"SELECT chat_id, group_name FROM allowed_groups WHERE {column_name} = 1")
    groups = cursor.fetchall()

    keyboard = [[InlineKeyboardButton(f"{group[1]} ({group[0]})", callback_data=f"confirm_remove_{group[0]}")] for group in groups]
    keyboard.append([InlineKeyboardButton("🔙 Abbrechen", callback_data=f"manage_bot_{bot_name}")])

    await query.message.edit_text("🗑️ Wähle eine Gruppe zum Entfernen:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Sicherheitsabfrage als Popup ---
async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("confirm_remove_", "")
    bot_name = context.user_data["selected_bot"]

    cursor.execute("SELECT group_name FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    group_name = cursor.fetchone()

    if group_name:
        keyboard = [
            [InlineKeyboardButton("✅ Ja, löschen", callback_data=f"delete_group_{chat_id}")],
            [InlineKeyboardButton("❌ Abbrechen", callback_data="remove_group")]
        ]
        await query.message.edit_text(
            f"⚠️ **Bist du sicher, dass du die Gruppe {group_name[0]} (`{chat_id}`) entfernen möchtest?**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.replace("delete_group_", "")
    bot_name = context.user_data["selected_bot"]
    column_name = f"allow_{bot_name.lower()}"

    cursor.execute("SELECT group_name FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    group_name = cursor.fetchone()

    cursor.execute(f"UPDATE allowed_groups SET {column_name} = 0 WHERE chat_id = ?", (chat_id,))
    conn.commit()

    await query.message.edit_text(
        f"✅ Gruppe **{group_name[0]}** (`{chat_id}`) wurde für {bot_name} entfernt.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Zurück zum Hauptmenü", callback_data="show_bots")]])
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_bots, pattern="^show_bots$"))
    app.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_bot_.*"))
    app.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    app.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove_.*"))
    app.add_handler(CallbackQueryHandler(delete_group, pattern="^delete_group_.*"))

    print("🤖 Bot gestartet! Warte auf Befehle...")
    app.run_polling()

if __name__ == "__main__":
    main()