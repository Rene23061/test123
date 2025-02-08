import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from datetime import datetime
import calendar

# Logging einrichten
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = "event_data.db"

# Datenbankverbindung herstellen
def set_event_date(chat_id: str, event_date: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO event_settings (chat_id, event_date)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET event_date=excluded.event_date
        ''', (chat_id, event_date))
        connection.commit()
        connection.close()
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Event-Datums: {e}")

def get_event_date(chat_id: str):
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("SELECT event_date FROM event_settings WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        connection.close()
        return result[0] if result else "Noch kein Datum gesetzt"
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Event-Datums: {e}")
        return "Fehler beim Laden des Datums"

# Inline-Kalender erstellen
def erstelle_inline_kalender() -> InlineKeyboardMarkup:
    today = datetime.today()
    jahr, monat = today.year, today.month
    cal = calendar.monthcalendar(jahr, monat)
    tastatur = []

    # Kalender-Tastatur erstellen
    for woche in cal:
        reihe = []
        for tag in woche:
            if tag == 0 or (monat == today.month and tag < today.day):
                reihe.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                reihe.append(InlineKeyboardButton(str(tag), callback_data=f"tag_{tag}_{monat}_{jahr}"))
        tastatur.append(reihe)

    return InlineKeyboardMarkup(tastatur)

# Zeit-Tastatur erstellen
def erstelle_zeit_tastatur() -> InlineKeyboardMarkup:
    zeiten = [("10:00 - 12:00", "10_12"), ("12:00 - 14:00", "12_14"), ("14:00 - 16:00", "14_16"),
              ("16:00 - 18:00", "16_18"), ("18:00 - 20:00", "18_20")]
    tastatur = [[InlineKeyboardButton(text, callback_data=f"zeit_{data}")] for text, data in zeiten]
    return InlineKeyboardMarkup(tastatur)

# /datum-Befehl im Gruppenchat
async def set_event_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if context.args:
        new_date = " ".join(context.args)
        set_event_date(chat_id, new_date)
        await update.message.reply_text(f"Das Event-Datum wurde auf **{new_date}** gesetzt.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Bitte gib ein Datum im Format TT.MM.JJJJ an: `/datum TT.MM.JJJJ`")

# /start im privaten Chat – zeigt den Kalender an
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_id = str(update.effective_chat.id)
    group_id = user_chat_id  # Verknüpfte Gruppen-ID finden wir später

    # Kalender anzeigen
    tastatur = erstelle_inline_kalender()
    await update.message.reply_text(
        "Wähle ein Datum aus dem Kalender:", reply_markup=tastatur
    )

# Datumsauswahl verarbeiten
async def tag_ausgewaehlt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tag, monat, jahr = query.data.split("_")
    context.user_data['ausgewaehltes_datum'] = f"{int(tag):02d}.{int(monat):02d}.{jahr}"
    tastatur = erstelle_zeit_tastatur()
    await query.edit_message_text("Wähle eine Uhrzeit:", reply_markup=tastatur)

# Zeitverarbeitung und Buchung speichern
async def zeit_ausgewaehlt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, start, ende = query.data.split("_")
    ausgewaehlte_zeit = f"{start}:00 - {ende}:00"

    # Buchungsdaten sammeln
    datum = context.user_data['ausgewaehltes_datum']
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    # Speichern der Buchung
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    cursor.execute('''
        INSERT INTO bookings (user_id, user_name, datum, zeit)
        VALUES (?, ?, ?, ?)
    ''', (user_id, user_name, datum, ausgewaehlte_zeit))
    connection.commit()
    connection.close()

    # Buchungsbestätigung
    await query.edit_message_text(
        f"Deine Buchung wurde bestätigt:\nDatum: {datum}\nZeit: {ausgewaehlte_zeit}"
    )

# Hauptprogramm
if __name__ == "__main__":
    app = ApplicationBuilder().token("DEIN_BOT_TOKEN").build()
    app.add_handler(CommandHandler("datum", set_event_date_command))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(tag_ausgewaehlt, pattern="^tag_"))
    app.add_handler(CallbackQueryHandler(zeit_ausgewaehlt, pattern="^zeit_"))
    app.run_polling()