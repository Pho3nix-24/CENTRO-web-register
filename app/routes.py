import os
from datetime import datetime
from functools import wraps # Importante para el decorador
from flask import render_template, request, redirect, url_for, flash, send_file, session

from app import app
from app.models import (
    EXCEL_FILE, HEADERS, FIELDS, agregar_registro, verificar_duplicado, 
    buscar_registros, obtener_datos_fila, actualizar_fila, eliminar_fila, generar_reporte_asesores
)

# --- DECORADOR PARA PROTEGER RUTAS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para ver esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE LOGIN Y LOGOUT ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Credenciales definidas
        if username == "centro-admin" and password == "centro-admin":
            session['logged_in'] = True
            flash("Has iniciado sesión correctamente.", "success")
            return redirect(url_for("index"))
        else:
            flash("Credenciales incorrectas. Inténtalo de nuevo.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    flash("Has cerrado la sesión.", "success")
    return redirect(url_for('login'))

# --- RUTAS PROTEGIDAS ---
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/descargar")
@login_required
def descargar():
    if not os.path.exists(EXCEL_FILE):
        flash("Error: El archivo de registros no existe.", "error")
        return redirect(url_for('index'))
    return send_file(EXCEL_FILE, as_attachment=True, download_name="registros.xlsx")

@app.route("/submit", methods=["POST"])
@login_required
def submit():
    data = request.form.to_dict()
    dni_nuevo = data.get("dni", "").strip()
    num_operacion_nuevo = data.get("num_operacion", "").strip()
    mensaje_error = verificar_duplicado(dni_nuevo, num_operacion_nuevo)
    if mensaje_error:
        flash(mensaje_error, "error")
        return redirect(url_for("index"))
    try:
        agregar_registro(data)
        flash("Registro guardado correctamente.", "success")
    except Exception as e:
        flash(f"Error al guardar el registro: {e}", "error")
    return redirect(url_for("index"))

@app.route("/consulta", methods=["GET"])
@login_required
def consulta():
    query = request.args.get("query", "").strip().lower()
    if query:
        resultados = buscar_registros(query)
    else:
        resultados = None
    return render_template("consulta.html", resultados=resultados, headers=HEADERS)

# --- NUEVA RUTA PARA LOS REPORTES ---
@app.route("/reportes")
@login_required
def reportes():
    """Muestra la página de reportes de ventas por asesor, desglosado por fecha."""
    reporte_crudo = generar_reporte_asesores()

    # Ordenar las fechas dentro de cada asesor (de más reciente a más antigua)
    for asesor, data in reporte_crudo.items():
        fechas_ordenadas = sorted(
            data['fechas'].items(), 
            key=lambda item: item[0], 
            reverse=True
        )
        reporte_crudo[asesor]['fechas'] = dict(fechas_ordenadas)

    # Ordenar el reporte principal por el total de ventas del asesor (de mayor a menor)
    reporte_ordenado = sorted(
        reporte_crudo.items(), 
        key=lambda item: item[1]['total_asesor'], 
        reverse=True
    )

    # Calcular totales generales
    total_general_ventas = sum(data['total_asesor'] for data in reporte_crudo.values())
    total_general_registros = sum(data['registros_asesor'] for data in reporte_crudo.values())

    return render_template(
        "reportes.html", 
        reporte=reporte_ordenado,
        total_ventas=total_general_ventas,
        total_registros=total_general_registros
    )

@app.route("/actualizar_pago/<int:fila_idx>", methods=["GET", "POST"])
@login_required
def actualizar_pago(fila_idx):
    if request.method == "POST":
        datos_originales = obtener_datos_fila(fila_idx)
        nuevos_datos_pago = request.form.to_dict()
        nuevo_registro = datos_originales.copy()
        nuevo_registro.update(nuevos_datos_pago)
        nuevo_registro['fecha'] = datetime.now().strftime('%Y-%m-%d')
        agregar_registro(nuevo_registro)
        flash("Nuevo pago registrado exitosamente como una nueva entrada.", "success")
        return redirect(url_for("consulta", query=request.args.get('query', '')))
    
    datos_actuales = obtener_datos_fila(fila_idx)
    query_original = request.args.get('query', '')
    return render_template("actualizar_pago.html", data=datos_actuales, fila_idx=fila_idx, query=query_original)

@app.route("/editar/<int:fila_idx>", methods=["GET", "POST"])
@login_required
def editar(fila_idx):
    if request.method == "POST":
        form_data = request.form.to_dict()
        actualizar_fila(fila_idx, form_data)
        flash("Registro actualizado correctamente.", "success")
        query = form_data.get("query", "")
        return redirect(url_for("consulta", query=query))
    data = obtener_datos_fila(fila_idx)
    labels_and_fields = list(zip(HEADERS, FIELDS))
    query_original = request.args.get('query', '')
    return render_template("editar.html", data=data, labels_and_fields=labels_and_fields, fila_idx=fila_idx, query=query_original)

@app.route("/eliminar", methods=["POST"])
@login_required
def eliminar():
    fila_idx = int(request.form.get("fila_idx"))
    query = request.form.get("query", "")
    if eliminar_fila(fila_idx):
        flash("Registro eliminado correctamente.", "success")
    else:
        flash("Error: No se pudo eliminar el registro.", "error")
    return redirect(url_for("consulta", query=query))