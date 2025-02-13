import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- Telegram-Bot-Token ---
TOKEN = "7675671508:AAGCGHAnFUWtVb57CRwaPSxlECqaLpyjRXM"

# --- Passwort für Admin-Zugang ---
ADMIN_PASSWORD = "Shorty2306"

# --- Verbindung zur SQLite-Datenbank herstellen ---
def init_db():
    conn = sqlite3.connect("whitelist.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            link TEXT,
            PRIMARY KEY (chat_id, link)
        )
    """)

    conn.commit()
    print("Datenbank erfolgreich initialisiert.")
    return conn, cursor

# --- Prüfen, ob die Gruppe erlaubt ist ---
def is_group_allowed(chat_id, cursor):
    cursor.execute("SELECT chat_id FROM allowed_groups WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone() is not None

# --- /start-Befehl mit Passwortabfrage ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Zugang erhalten", callback_data="enter_password")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Bitte bestätige dein Passwort, um fortzufahren:", reply_markup=reply_markup)

# --- Passwort-Eingabe ---
async def enter_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("Bitte sende dein Passwort als Nachricht.")

    context.user_data["awaiting_password"] = True

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        if update.message.text == ADMIN_PASSWORD:
            context.user_data["authenticated"] = True
            keyboard = [
                [InlineKeyboardButton("Gruppen-ID anzeigen", callback_data="show_group_id")],
                [InlineKeyboardButton("Whitelist verwalten", callback_data="manage_whitelist")],
                [InlineKeyboardButton("Links verwalten", callback_data="manage_links")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Zugriff gewährt! Wähle eine Aktion:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Falsches Passwort! Bitte versuche es erneut.")

        context.user_data["awaiting_password"] = False

# --- Gruppen-ID anzeigen ---
async def show_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.message.edit_text(
        f"Die Gruppen-ID ist: `{chat_id}`", 
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Zurück", callback_data="back_to_menu")]
        ])
    )

# --- Whitelist-Verwaltung ---
async def manage_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Gruppe hinzufügen", callback_data="add_group")],
        [InlineKeyboardButton("Gruppe entfernen", callback_data="remove_group")],
        [InlineKeyboardButton("Erlaubte Gruppen anzeigen", callback_data="list_groups")],
        [InlineKeyboardButton("Zurück", callback_data="back_to_menu")]
    ]
    await query.message.edit_text("Whitelist-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("Sende die Gruppen-ID, die du hinzufügen möchtest.")
    context.user_data["awaiting_group_add"] = True

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("Sende die Gruppen-ID, die du entfernen möchtest.")
    context.user_data["awaiting_group_remove"] = True

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cursor.execute("SELECT chat_id FROM allowed_groups")
    groups = cursor.fetchall()
    
    if groups:
        response = "Erlaubte Gruppen:\n" + "\n".join(f"- `{group[0]}`" for group in groups)
    else:
        response = "Es sind keine Gruppen erlaubt."
    
    await query.message.edit_text(response, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Zurück", callback_data="back_to_menu")]
    ]))

# --- Links-Verwaltung ---
async def manage_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Link hinzufügen", callback_data="add_link")],
        [InlineKeyboardButton("Link entfernen", callback_data="remove_link")],
        [InlineKeyboardButton("Erlaubte Links anzeigen", callback_data="list_links")],
        [InlineKeyboardButton("Zurück", callback_data="back_to_menu")]
    ]
    await query.message.edit_text("Link-Verwaltung:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Zurück zum Hauptmenü ---
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await start(query.message, context)

# --- Hauptfunktion zum Starten des Bots ---
def main():
    global conn, cursor
    conn, cursor = init_db()

    application = Application.builder().token(TOKEN).build()

    # Befehle hinzufügen
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))

    # Inline-Menü Handler
    application.add_handler(CallbackQueryHandler(enter_password, pattern="^enter_password$"))
    application.add_handler(CallbackQueryHandler(show_group_id, pattern="^show_group_id$"))
    application.add_handler(CallbackQueryHandler(manage_whitelist, pattern="^manage_whitelist$"))
    application.add_handler(CallbackQueryHandler(add_group, pattern="^add_group$"))
    application.add_handler(CallbackQueryHandler(remove_group, pattern="^remove_group$"))
    application.add_handler(CallbackQueryHandler(list_groups, pattern="^list_groups$"))
    application.add_handler(CallbackQueryHandler(manage_links, pattern="^manage_links$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))

    print("Bot gestartet! Warte auf Befehle...")
    application.run_polling()

if __name__ == "__main__":
    main()