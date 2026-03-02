import os
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")
MY_ID = int(os.getenv("MY_ID"))
PASSWORD_CORRECTA = "Carlos13mar"

config = {
    "link_grupo": "Configura un link para grupos",
    "link_privado": "Configura un link para privados",
    "intervalo": 600,
    "autorizados": {MY_ID},
    "tareas_activas": {} 
}

# --- SERVIDOR WEB ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Operativo")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), SimpleHandler).serve_forever()

# --- LÓGICA DE ENVÍO ---
async def bucle_spam(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    while True:
        try:
            await context.bot.send_message(chat_id=chat_id, text=config["link_grupo"])
        except Exception as e:
            logging.error(f"Error en grupo {chat_id}: {e}")
        await asyncio.sleep(config["intervalo"])

# --- TECLADOS ---
def menu_principal():
    keyboard = [
        [InlineKeyboardButton("Mensaje a grupo 👥", callback_data="menu_grupo")],
        [InlineKeyboardButton("Mensaje privado 👤", callback_data="menu_privado")]
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_grupo_config():
    keyboard = [
        [InlineKeyboardButton("Enviar Link 🔗", callback_data="set_link_g")],
        [InlineKeyboardButton("Seleccionar Tiempo ⏱", callback_data="set_time")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def teclado_tiempos():
    keyboard = [
        [InlineKeyboardButton("10m", callback_data="t_600"), InlineKeyboardButton("20m", callback_data="t_1200")],
        [InlineKeyboardButton("30m", callback_data="t_1800"), InlineKeyboardButton("1h", callback_data="t_3600")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="menu_grupo")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- MANEJADORES ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Respuesta a usuario RANDOM (Privado)
    if update.message.chat.type == "private" and user_id not in config["autorizados"]:
        await update.message.reply_text(config["link_privado"])
        return

    # Menú para el DUEÑO (Privado)
    if update.message.chat.type == "private" and user_id in config["autorizados"]:
        await update.message.reply_text("Panel de Administración:", reply_markup=menu_principal())
        return

    # Activación en GRUPO (Sin mensaje de confirmación)
    if user_id in config["autorizados"] and chat_id not in config["tareas_activas"]:
        task = asyncio.create_task(bucle_spam(context, chat_id))
        config["tareas_activas"][chat_id] = task

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == PASSWORD_CORRECTA:
        config["autorizados"].add(user_id)
        await update.message.reply_text("✅ Acceso admin activado.", reply_markup=menu_principal())
        return

    if user_id in config["autorizados"] and update.message.chat.type == "private":
        state = context.user_data.get("state")
        if state == "waiting_link_g":
            config["link_grupo"] = text
            await update.message.reply_text(f"✅ Link de GRUPO actualizado.", reply_markup=menu_grupo_config())
        elif state == "waiting_link_p":
            config["link_privado"] = text
            await update.message.reply_text(f"✅ Link de PRIVADO actualizado.", reply_markup=menu_principal())
        context.user_data["state"] = None

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config["autorizados"]: return

    if query.data == "main":
        await query.edit_message_text("Panel de Administración:", reply_markup=menu_principal())
    elif query.data == "menu_grupo":
        await query.edit_message_text(f"Configuración de Grupos\nLink actual: {config['link_grupo']}", reply_markup=menu_grupo_config())
    elif query.data == "menu_privado":
        await query.edit_message_text("Configuración de Privados\nUsa el botón para cambiar el link que verán los usuarios random.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar Link 🔗", callback_data="set_link_p")], [InlineKeyboardButton("⬅️ Volver", callback_data="main")]]))
    elif query.data == "set_link_g":
        context.user_data["state"] = "waiting_link_g"
        await query.edit_message_text("Envíame el nuevo link para los GRUPOS:")
    elif query.data == "set_link_p":
        context.user_data["state"] = "waiting_link_p"
        await query.edit_message_text("Envíame el nuevo link para los PRIVADOS (usuarios random):")
    elif query.data == "set_time":
        await query.edit_message_text("Selecciona el intervalo de tiempo:", reply_markup=teclado_tiempos())
    elif query.data.startswith("t_"):
        config["intervalo"] = int(query.data.split("_")[1])
        await query.edit_message_text(f"✅ Tiempo actualizado a {config['intervalo']//60} min.", reply_markup=menu_grupo_config())

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == '__main__':
    main()
