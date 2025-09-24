import os
from datetime import datetime
from functools import wraps
from flask import (
    render_template, request, redirect, url_for, 
    flash, session, send_file, send_from_directory
)
from app import app
from app import database_manager as db
from mysql.connector import Error as DB_Error

# --- LISTA DE USUARIOS AUTORIZADOS ---
USERS = {
    'admin': {'password': 'centro-admin', 'full_name': 'Administrador'},
    'lud_rojas': {'password': 'centro', 'full_name': 'Lud Rojas'},
    'ruth_lecca': {'password': 'centro', 'full_name': 'Ruth Lecca'},
    'rafa_diaz': {'password': 'centro', 'full_name': 'Rafael Díaz'}
}

# --- CAMPOS Y COLUMNAS ---
RECORDS_PER_PAGE = 5 #Paginación en reportes
HEADERS = [
    "FECHA", "CLIENTE", "CELULAR", "ESPECIALIDAD", "MODALIDAD", "CUOTA", 
    "TIPO DE CUOTA", "BANCO", "DESTINO", "N° OPERACIÓN", "DNI", "CORREO", 
    "GÉNERO", "ASESOR"
]
FIELDS = [
    "fecha", "cliente", "celular", "especialidad", "modalidad", "cuota", 
    "tipo_de_cuota", "banco", "destino", "numero_operacion", "dni", 
    "correo", "genero", "asesor"
]

# Ruta decorada para verificar si el usuario ha iniciado sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para ver esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_data = USERS.get(username)
        
        if user_data and user_data['password'] == password:
            session['logged_in'] = True
            session['full_name'] = user_data['full_name'] # Para el saludo "Hola, Lud Rojas"
            session['username'] = username  # <-- AÑADIDO: Para verificar si es admin
            
            ip_usuario = request.remote_addr
            db.registrar_auditoria(user_data['full_name'], "INICIO_SESION_EXITOSO", ip_usuario)

            flash("Has iniciado sesión correctamente.", "success")
            return redirect(url_for("index"))
        else:
            ip_usuario = request.remote_addr
            # Registramos el intento fallido con el usuario que se intentó usar
            db.registrar_auditoria(username, "INICIO_SESION_FALLIDO", ip_usuario)
            flash("Credenciales incorrectas. Inténtalo de nuevo.", "error")
            
    return render_template("login.html")

#Ruta logout
@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    flash("Has cerrado la sesión.", "success")
    return redirect(url_for('login'))

# --- Rutas Principales de la Aplicación ---

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
@login_required
def submit():
    form_data = request.form.to_dict()
    try:
        cliente_id = db.buscar_o_crear_cliente(form_data)
        # ... (el resto de tu lógica para preparar form_data) ...
        
        # Guardamos el ID del nuevo pago que se va a crear
        nuevo_pago_id = db.crear_pago(cliente_id, form_data)
        flash("Registro guardado correctamente.", "success")

        # ¡Registramos la acción de auditoría!
        usuario_actual = session.get('username', 'desconocido')
        ip_usuario = request.remote_addr
        detalles = f"Cliente ID: {cliente_id}, Pago ID: {nuevo_pago_id}"
        db.registrar_auditoria(usuario_actual, "CREAR_PAGO", ip_usuario, "pagos", nuevo_pago_id, detalles)

    except DB_Error as e:
        flash(f"Error al guardar el registro: {e}", "error")
    return redirect(url_for("index"))

@app.route("/consulta", methods=["GET"])
@login_required
def consulta():
    query = request.args.get("query", "").strip().lower()
    resultados = []
    try:
        if query:
            resultados = db.buscar_pagos_completos(query)
    except DB_Error as e:
        flash(f"Error al consultar la base de datos: {e}", "error")
    headers_db = ["ID"] + HEADERS
    return render_template("consulta.html", resultados=resultados, headers=headers_db)

@app.route("/reportes")
@login_required
def reportes():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)

        reporte_completo_db = db.generar_reporte_asesores_db(start_date, end_date)
        
        total_records = len(reporte_completo_db)
        total_pages = (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE if RECORDS_PER_PAGE > 0 else 1
        start_index = (page - 1) * RECORDS_PER_PAGE
        end_index = start_index + RECORDS_PER_PAGE
        reporte_paginado_db = reporte_completo_db[start_index:end_index]

        total_general_ventas = sum(item.get('total_asesor', 0) or 0 for item in reporte_completo_db)
        total_general_registros = sum(item.get('registros_asesor', 0) for item in reporte_completo_db)
        
        page_total_ventas = sum(item.get('total_asesor', 0) or 0 for item in reporte_paginado_db)
        page_total_registros = sum(item.get('registros_asesor', 0) for item in reporte_paginado_db)
        
        reporte_para_plantilla = [(item['asesor'], item) for item in reporte_paginado_db]
        
        return render_template(
            "reportes.html", reporte=reporte_para_plantilla, total_ventas=total_general_ventas,
            total_registros=total_general_registros, start_date=start_date, end_date=end_date,
            page=page, total_pages=total_pages, page_total_ventas=page_total_ventas,
            page_total_registros=page_total_registros
        )
    except DB_Error as e:
        flash(f"Error al generar el reporte: {e}", "error")
        return render_template("reportes.html", reporte=[])

@app.route("/actualizar_pago/<int:id>", methods=["GET", "POST"])
@login_required
def actualizar_pago(id):
    if request.method == "POST":
        try:
            pago_original = db.obtener_pago_por_id(id)
            if not pago_original:
                flash("Error: No se encontró el registro original.", "error")
                return redirect(url_for("consulta"))

            cliente_id = pago_original['cliente_id']
            datos_nuevo_pago = request.form.to_dict()
            datos_nuevo_pago['fecha'] = datetime.now()
            datos_nuevo_pago['numero_operacion'] = datos_nuevo_pago.pop('num_operacion', None)
            
            # Completamos datos que no vienen en el formulario simple de pago
            datos_nuevo_pago['especialidad'] = pago_original['especialidad']
            datos_nuevo_pago['modalidad'] = pago_original['modalidad']
            datos_nuevo_pago['asesor'] = pago_original['asesor']
            
            db.crear_pago(cliente_id, datos_nuevo_pago)
            flash("Renovación de pago registrada exitosamente.", "success")
            return redirect(url_for("consulta", query=request.args.get('query', '')))
        except DB_Error as e:
            flash(f"Error al procesar el pago: {e}", "error")
            return redirect(url_for("consulta", query=request.args.get('query', '')))
    
    datos_pago_actual = db.obtener_pago_por_id(id)
    return render_template("actualizar_pago.html", data=datos_pago_actual, id=id, query=request.args.get('query', ''))

@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    if request.method == "POST":
        form_data = request.form.to_dict()
        try:
            db.actualizar_pago(id, form_data)
            flash("Pago actualizado correctamente.", "success")
        except DB_Error as e:
            flash(f"Error al actualizar el pago: {e}", "error")
        return redirect(url_for("consulta", query=form_data.get("query", "")))
    
    data = db.obtener_pago_por_id(id)
    labels_and_fields = list(zip(HEADERS, FIELDS))
    return render_template("editar.html", data=data, labels_and_fields=labels_and_fields, id=id, query=request.args.get('query', ''))

@app.route("/eliminar", methods=["POST"])
@login_required
def eliminar():
    pago_id = int(request.form.get("id"))
    query = request.form.get("query", "")
    try:
        db.eliminar_pago(pago_id)
        flash("Registro de pago eliminado correctamente.", "success")
    except DB_Error as e:
        flash(f"Error: No se pudo eliminar el registro de pago: {e}", "error")
    return redirect(url_for("consulta", query=query))

@app.route("/descargar")
@login_required
def descargar():
    try:
        output = db.generar_excel_dinamico(HEADERS)
        if output:
            return send_file(
                output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True, download_name='registros_db.xlsx'
            )
        else:
            flash("Error al generar el archivo Excel.", "error")
            return redirect(url_for('index'))
    except DB_Error as e:
        flash(f"Error al generar el archivo Excel: {e}", "error")
        return redirect(url_for('index'))
    
# Ruta Auditoria de accesos (solo admin)
@app.route("/auditoria")
@login_required
def auditoria():
    if session.get('username') != 'admin':
        flash("Acceso no autorizado.", "error")
        return redirect(url_for('index'))
    logs = db.leer_log_auditoria()
    return render_template("auditoria.html", logs=logs)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 'icon.png', mimetype='image/png')