import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT

TOKEN = "7770444877:AAEYnWtxNtGKBXGlIQ77yAVjhl_C0d3uK9Y"

def get_database_connection():
    conn = sqlite3.connect('booking_bot.db')
    return conn

def fetch_events():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, event_name, event_date FROM events")
    events = cursor.fetchall()
    conn.close()
    return events

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    await update.message.reply_text(f"Hallo {user.first_name}! Hier sind die aktuellen Events:")

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

async def event_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    selected_event_id = int(query.data)
    context.user_data['selected_event_id'] = selected_event_id
    events = fetch_events()
    selected_event = [event for event in events if event[0] == selected_event_id][0]

    keyboard = [
        [InlineKeyboardButton("13-16 Uhr (100€ / 30€)", callback_data="1"), 
         InlineKeyboardButton("17-20 Uhr (100€ / 30€)", callback_data="2")],
        [InlineKeyboardButton("13-20 Uhr (150€ / 50€)", callback_data="3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Du hast das Event '{selected_event[1]}' am {selected_event[2]} ausgewählt.\nBitte wähle ein Zeitfenster:",
        reply_markup=reply_markup
    )

async def time_slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    time_slot = query.data
    context.user_data['selected_time_slot'] = time_slot

    time_slots = {"1": "13 bis 16 Uhr", "2": "17 bis 20 Uhr", "3": "13 bis 20 Uhr"}

    await query.edit_message_text(
        f"Du hast das Zeitfenster '{time_slots[time_slot]}' ausgewählt.\n"
        "Bitte schreibe jetzt deine Wünsche oder Anmerkungen für das Event."
    )

async def save_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wishes = update.message.text
    context.user_data['wishes'] = wishes

    await update.message.reply_text(
        f"Deine Wünsche wurden gespeichert: \"{wishes}\".\nBitte wähle eine Zahlungsmethode:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Amazon-Gutschein", callback_data="amazon")],
            [InlineKeyboardButton("PayPal", callback_data="paypal")],
            [InlineKeyboardButton("Revolut", callback_data="revolut")]
        ])
    )

async def payment_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    payment_method = query.data
    context.user_data['payment_method'] = payment_method

    time_slots = {"1": "13 bis 16 Uhr", "2": "17 bis 20 Uhr", "3": "13 bis 20 Uhr"}
    selected_time_slot = context.user_data['selected_time_slot']
    wishes = context.user_data.get('wishes', 'Keine besonderen Wünsche')

    await query.edit_message_text(
        f"🎉 Buchung erfolgreich! Hier sind deine Details:\n\n"
        f"⏰ Zeitfenster: {time_slots[selected_time_slot]}\n"
        f"💬 Wünsche: {wishes}\n"
        f"💳 Zahlungsmethode: {payment_method}\n"
        "Ein Administrator wird dich kontaktieren. Danke!"
    )

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(event_selected, pattern='^\\d+$'))
    application.add_handler(CallbackQueryHandler(time_slot_selected, pattern='^[123]$'))
    application.add_handler(MessageHandler(TEXT, save_wishes))
    application.add_handler(CallbackQueryHandler(payment_selected, pattern='^(amazon|paypal|revolut)$'))
    application.run_polling()

if __name__ == "__main__":
    main()