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
    "fijar": False, # <--- Opción de fijado recuperada
    "autorizados": {MY_ID},
    "tareas_activas": {} 
}

# --- SERVIDOR WEB ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.
