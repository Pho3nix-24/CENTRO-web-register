# app/__init__.py
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = "CENTRO-WEB-2025"

# Importar las rutas al final para evitar importaciones circulares
from app import routes