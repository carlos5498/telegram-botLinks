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
MY_ID = int(os.getenv("MY_ID"))  # Tu ID numérico
PASSWORD_CORRECTA = "Carlos13mar"

# Variables globales en memoria (puedes pasarlas a MongoDB después si quieres)
config_spam = {
    "link": "https://telegra.ph/Tu-Enlace-Aqui",
    "intervalo": 600,  # 10 min por defecto
    "fijar": False,
    "autorizados": {MY_ID},
    "tareas_activas": {} # {chat_id: task}
}

# --- SERVIDOR WEB (Para que Render no se apague) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Spam Activo")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# --- FUNCIONES DE SPAM ---
async def tarea_spam(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    while True:
        try:
            msg = await context.bot.send_message(
                chat_id=chat_id, 
                text=f"📢 **Aviso Oficial**\n\n{config_spam['link']}",
                parse_mode="Markdown"
            )
            if config_spam["fijar"]:
                await context.bot.pin_chat_message(chat_id, msg.message_id)
        except Exception as e:
            logging.error(f"Error en spam: {e}")
        
        await asyncio.sleep(config_spam["intervalo"])

# --- TECLADOS ---
def teclado_config():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 Min", callback_data="t_600"), InlineKeyboardButton("20 Min", callback_data="t_1200")],
        [InlineKeyboardButton("30 Min", callback_data="t_1800"), InlineKeyboardButton("1 Hora", callback_data="t_3600")],
        [
            InlineKeyboardButton("📌 Fijar: ON" if config_spam["fijar"] else "📌 Fijar: OFF", callback_data="toggle_pin")
        ]
    ])

# --- MANEJADORES ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Caso Privado: Configuración
    if update.message.chat.type == "private":
        if user_id in config_spam["autorizados"]:
            await update.message.reply_text(
                f"⚙️ **Panel de Control**\nLink actual: {config_spam['link']}\nIntervalo: {config_spam['intervalo']//60} min",
                reply_markup=teclado_config()
            )
        return

    # Caso Grupo: Iniciar Spam
    if user_id in config_spam["autorizados"]:
        if chat_id not in config_spam["tareas_activas"]:
            # Crear tarea asíncrona para este grupo
            task = asyncio.create_task(tarea_spam(context, chat_id))
            config_spam["tareas_activas"][chat_id] = task
            await update.message.reply_text("🚀 **Spam iniciado con éxito en este grupo.**")
        else:
            await update.message.reply_text("⚠️ Ya hay un ciclo de spam activo aquí.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Si es la contraseña, autorizar
    if text == PASSWORD_CORRECTA:
        config_spam["autorizados"].add(user_id)
        await update.message.reply_text("✅ Acceso concedido. Ahora puedes mandarme el LINK o usar /start.")
        return

    # Si está autorizado y manda un link por privado
    if user_id in config_spam["autorizados"] and update.message.chat.type == "private":
        if "http" in text:
            config_spam["link"] = text
            await update.message.reply_text(f"🔗 Link actualizado a:\n{text}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config_spam["autorizados"]:
        return

    data = query.data
    if data.startswith("t_"):
        config_spam["intervalo"] = int(data.split("_")[1])
    elif data == "toggle_pin":
        config_spam["fijar"] = not config_spam["fijar"]

    await query.edit_message_text(
        f"⚙️ **Configuración Actualizada**\nLink: {config_spam['link']}\nIntervalo: {config_spam['intervalo']//60} min\nFijar: {'SI' if config_spam['fijar'] else 'NO'}",
        reply_markup=teclado_config()
    )

def main():
    # Iniciar servidor web en un hilo aparte
    threading.Thread(target=run_web_server, daemon=True).start()

    # Configurar la Aplicación de Telegram
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()

if __name__ == '__main__':
    main()
