from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT

# Dein Telegram-Bot-Testtoken (später das finale Token ersetzen!)
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

# Start-Nachricht
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    update.message.reply_text(f"Hallo {user.first_name}! Willkommen beim Buchungs-Bot.\n\nHier sind die aktuellen Events:")

    events = fetch_events()
    if events:
        event_list = "\n".join([f"{event[0]}. {event[1]} am {event[2]}" for event in events])
        update.message.reply_text(event_list)
        update.message.reply_text("Bitte sende die **Event-ID**, um ein Event auszuwählen.")
    else:
        update.message.reply_text("Aktuell sind keine Events verfügbar.")

# Event-Auswahl (noch ohne Speicherung)
def handle_event_selection(update: Update, context: CallbackContext) -> None:
    message = update.message.text.strip()
    if not message.isdigit():
        update.message.reply_text("Bitte sende eine gültige Event-ID.")
        return

    selected_event_id = int(message)
    events = fetch_events()
    event_ids = [event[0] for event in events]

    if selected_event_id in event_ids:
        context.user_data['selected_event_id'] = selected_event_id
        selected_event = [event for event in events if event[0] == selected_event_id][0]
        update.message.reply_text(f"Du hast das Event '{selected_event[1]}' am {selected_event[2]} ausgewählt.\n"
                                  f"Bitte wähle nun ein Zeitfenster:\n"
                                  f"1. 13 bis 16 Uhr (100€ mit 30€ Anzahlung)\n"
                                  f"2. 17 bis 20 Uhr (100€ mit 30€ Anzahlung)\n"
                                  f"3. 13 bis 20 Uhr (150€ mit 50€ Anzahlung)")
    else:
        update.message.reply_text("Ungültige Event-ID. Bitte sende eine gültige Event-ID.")

# Hauptfunktion zum Starten des Bots
def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Handler für den /start-Befehl
    dispatcher.add_handler(CommandHandler("start", start))

    # Handler für die Eingabe der Event-ID
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_event_selection))

    # Bot starten
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()