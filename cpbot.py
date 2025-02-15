from telegram import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Interaktive Link-Verwaltung ---
async def manage_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    # Prüfen, ob die Gruppe erlaubt ist
    if not is_group_allowed(chat_id):
        await update.message.reply_text("❌ Diese Gruppe ist nicht erlaubt, der Bot reagiert hier nicht.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Link hinzufügen", callback_data=f"add_link_{chat_id}")],
        [InlineKeyboardButton("📋 Whitelist anzeigen", callback_data=f"show_list_{chat_id}")]
    ]

    await update.message.reply_text(
        "🔗 **Link-Verwaltung:**\nWähle eine Option aus:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- Link hinzufügen: Fragt den Benutzer nach einem Link ---
async def add_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    await query.message.edit_text(
        "✏️ Bitte sende mir den **Link**, den du zur Whitelist hinzufügen möchtest."
    )

    context.user_data["waiting_for_link"] = chat_id  # Speichert, dass ein Link erwartet wird

# --- Link speichern ---
async def save_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("waiting_for_link")

    if not chat_id:
        return

    link = update.message.text.strip()

    # Prüfen, ob es ein Telegram-Link ist
    if not TELEGRAM_LINK_PATTERN.match(link):
        await update.message.reply_text("⚠️ Ungültiger Link! Bitte sende einen gültigen Telegram-Link.")
        return

    try:
        cursor.execute("INSERT INTO whitelist (chat_id, link) VALUES (?, ?)", (chat_id, link))
        conn.commit()

        await update.message.reply_text(f"✅ **{link}** wurde zur Whitelist hinzugefügt.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Dieser Link ist bereits in der Whitelist.")

    context.user_data.pop("waiting_for_link", None)  # Löscht den Status

# --- Whitelist anzeigen ---
async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Die Whitelist dieser Gruppe ist leer.")
        return

    keyboard = [[InlineKeyboardButton("❌ Entfernen", callback_data=f"delete_menu_{chat_id}")]]
    link_list = "\n".join(f"- {link[0]}" for link in links)

    await query.message.edit_text(
        f"📋 **Whitelist:**\n{link_list}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- Link-Löschmenü ---
async def delete_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.data.split("_")[-1]

    cursor.execute("SELECT link FROM whitelist WHERE chat_id = ?", (chat_id,))
    links = cursor.fetchall()

    if not links:
        await query.message.edit_text("❌ Die Whitelist ist leer.")
        return

    keyboard = [[InlineKeyboardButton(f"❌ {link[0]}", callback_data=f"delete_{chat_id}_{link[0]}")] for link in links]
    keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data=f"show_list_{chat_id}")])

    await query.message.edit_text(
        "🗑 **Wähle einen Link zum Löschen:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- Link löschen ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = data[1]
    link = "_".join(data[2:])  # Falls der Link Unterstriche enthält

    cursor.execute("DELETE FROM whitelist WHERE chat_id = ? AND link = ?", (chat_id, link))
    conn.commit()

    await query.answer(f"✅ {link} wurde gelöscht.", show_alert=True)
    await delete_link_menu(update, context)  # Aktualisiertes Menü anzeigen