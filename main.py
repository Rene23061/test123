import sqlite3

# Verbindung zur Datenbank herstellen
def get_database_connection():
    conn = sqlite3.connect('booking_bot.db')
    return conn

# Events aus der Datenbank abrufen
def fetch_events():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, event_name, event_date, time_slots FROM events")
    events = cursor.fetchall()
    conn.close()
    return events

# Buchungen aus der Datenbank abrufen
def fetch_bookings():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT booking_id, username, event_id, selected_time_slot, payment_method, wishes, booking_date FROM bookings")
    bookings = cursor.fetchall()
    conn.close()
    return bookings

# Teste die Funktionen
if __name__ == "__main__":
    print("Verfügbare Events:")
    events = fetch_events()
    for event in events:
        print(f"Event-ID: {event[0]}, Name: {event[1]}, Datum: {event[2]}, Zeitfenster: {event[3]}")
    
    print("\nBuchungen:")
    bookings = fetch_bookings()
    for booking in bookings:
        print(f"Buchung-ID: {booking[0]}, Benutzer: {booking[1]}, Event-ID: {booking[2]}, "
              f"Zeitfenster: {booking[3]}, Zahlungsmethode: {booking[4]}, Wünsche: {booking[5]}, "
              f"Buchungsdatum: {booking[6]}")
