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
# Convertimos MY_ID a entero, si no existe ponemos 0
try:
    MY_ID = int(os.getenv("MY_ID", "0"))
except:
    MY_ID = 0

PASSWORD_CORRECTA = "Carlos13mar"

config = {
    "link_grupo": "Configura un link para grupos",
    "link_privado": "Configura un link para privados",
    "intervalo": 600,
    "fijar": False,
    "autorizados": {MY_ID} if MY_ID != 0 else set(),
    "tareas_activas": {} 
}

# --- SERVIDOR WEB (Obligatorio para Render) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Operativo")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# --- LÓGICA DE ENVÍO ---
async def bucle_spam(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    while True:
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text=config["link_grupo"])
            if config["fijar"]:
                try:
                    await context.bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
                except Exception as e:
                    logging.error(f"Permisos insuficientes para fijar en {chat_id}")
        except Exception as e:
            logging.error(f"Error en grupo {chat_id}: {e}")
        await asyncio.sleep(config["intervalo"])

# --- TECLADOS ---
def menu_principal():
    keyboard = [[InlineKeyboardButton("Mensaje a grupo 👥", callback_data="menu_grupo")],
                [InlineKeyboardButton("Mensaje privado 👤", callback_data="menu_privado")]]
    return InlineKeyboardMarkup(keyboard)

def menu_grupo_config():
    txt_fijar = "📌 Fijar: ON" if config["fijar"] else "📌 Fijar: OFF"
    keyboard = [[InlineKeyboardButton("Enviar Link 🔗", callback_data="set_link_g")],
                [InlineKeyboardButton("Seleccionar Tiempo ⏱", callback_data="set_time")],
                [InlineKeyboardButton(txt_fijar, callback_data="toggle_pin")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="main")]]
    return InlineKeyboardMarkup(keyboard)

def teclado_tiempos():
    keyboard = [[InlineKeyboardButton("10m", callback_data="t_600"), InlineKeyboardButton("20m", callback_data="t_1200")],
                [InlineKeyboardButton("30m", callback_data="t_1800"), InlineKeyboardButton("1h", callback_data="t_3600")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="menu_grupo")]]
    return InlineKeyboardMarkup(keyboard)

# --- MANEJADORES ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if update.message.chat.type == "private":
        if user_id not in config["autorizados"]:
            await update.message.reply_text(config["link_privado"])
            return
        await update.message.reply_text("Panel de Administración:", reply_markup=menu_principal())
        return

    if user_id in config["autorizados"] and chat_id not in config["tareas_activas"]:
        config["tareas_activas"][chat_id] = asyncio.create_task(bucle_spam(context, chat_id))

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
            await update.message.reply_text("✅ Link de GRUPO actualizado.", reply_markup=menu_grupo_config())
        elif state == "waiting_link_p":
            config["link_privado"] = text
            await update.message.reply_text("✅ Link de PRIVADO actualizado.", reply_markup=menu_principal())
        context.user_data["state"] = None

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in config["autorizados"]: return

    if query.data == "main":
        await query.edit_message_text("Panel de Administración:", reply_markup=menu_principal())
    elif query.data == "menu_grupo":
        await query.edit_message_text(f"Configuración Grupos\nLink: {config['link_grupo']}", reply_markup=menu_grupo_config())
    elif query.data == "menu_privado":
        await query.edit_message_text(f"Configuración Privados\nLink: {config['link_privado']}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar Link 🔗", callback_data="set_link_p")], [InlineKeyboardButton("⬅️ Volver", callback_data="main")]]))
    elif query.data == "set_link_g":
        context.user_data["state"] = "waiting_link_g"; await query.edit_message_text("Envíame el nuevo link para GRUPOS:")
    elif query.data == "set_link_p":
        context.user_data["state"] = "waiting_link_p"; await query.edit_message_text("Envíame el nuevo link para PRIVADOS:")
    elif query.data == "set_time":
        await query.edit_message_text("Selecciona intervalo:", reply_markup=teclado_tiempos())
    elif query.data == "toggle_pin":
        config["fijar"] = not config["fijar"]
        await query.edit_message_reply_markup(reply_markup=menu_grupo_config())
    elif query.data.startswith("t_"):
        config["intervalo"] = int(query.data.split("_")[1])
        await query.edit_message_text(f"✅ Tiempo: {config['intervalo']//60} min.", reply_markup=menu_grupo_config())

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == '__main__':
    main()
