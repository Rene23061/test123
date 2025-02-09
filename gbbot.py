import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Dein Telegram-Bot-Testtoken
TOKEN = "7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y"

# Verbindung zur Datenbank herstellen
def get_database_connection():
    conn = sqlite3.connect('booking_bot.db')
    return conn

# Events aus der Datenbank abrufen
def fetch_events():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, event_name, event_date FROM events")
    events = cursor.fetchall()
    conn.close()
    return events

# Start-Nachricht mit Event-Buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    await update.message.reply_text(f"Hallo {user.first_name}! Willkommen beim Buchungs-Bot.\nHier sind die aktuellen Events:")

    events = fetch_events()
    if events:
        keyboard = [
            [InlineKeyboardButton(f"{event[1]} am {event[2]}", callback_data=str(event[0]))]
            for event in events
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Bitte wähle ein Event aus:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Aktuell sind keine Events verfügbar.")

# Event-Auswahl verarbeiten
async def event_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    selected_event_id = int(query.data)
    context.user_data['selected_event_id'] = selected_event_id
    events = fetch_events()
    selected_event = [event for event in events if event[0] == selected_event_id][0]

    keyboard = [
        [InlineKeyboardButton("13 bis 16 Uhr (100€ / 30€ Anzahlung)", callback_data="1")],
        [InlineKeyboardButton("17 bis 20 Uhr (100€ / 30€ Anzahlung)", callback_data="2")],
        [InlineKeyboardButton("13 bis 20 Uhr (150€ / 50€ Anzahlung)", callback_data="3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Du hast das Event '{selected_event[1]}' am {selected_event[2]} ausgewählt.\nBitte wähle ein Zeitfenster:",
        reply_markup=reply_markup
    )

# Zeitauswahl verarbeiten
async def time_slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    time_slot = query.data
    context.user_data['selected_time_slot'] = time_slot

    time_slots = {
        "1": "13 bis 16 Uhr (100€ / 30€ Anzahlung)",
        "2": "17 bis 20 Uhr (100€ / 30€ Anzahlung)",
        "3": "13 bis 20 Uhr (150€ / 50€ Anzahlung)"
    }

    await query.edit_message_text(
        f"Du hast das Zeitfenster '{time_slots[time_slot]}' ausgewählt.\n"
        "Bitte teile uns mit, ob du besondere Wünsche oder Anmerkungen für das Event hast."
    )

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(event_selected, pattern='^\\d+$'))
    application.add_handler(CallbackQueryHandler(time_slot_selected, pattern='^[123]$'))
    application.run_polling()

if __name__ == "__main__":
    main()