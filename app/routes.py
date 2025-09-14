import os
from datetime import datetime # Importar datetime
from flask import render_template, request, redirect, url_for, flash, send_file

from app import app
from app.models import (
    EXCEL_FILE, HEADERS, FIELDS, agregar_registro, verificar_duplicado, 
    buscar_registros, obtener_datos_fila, actualizar_fila, eliminar_fila
)

@app.route("/")
def index():
    """Muestra el formulario de registro."""
    return render_template("index.html")

@app.route("/descargar")
def descargar():
    """Permite descargar el archivo Excel usando la ruta absoluta."""
    if not os.path.exists(EXCEL_FILE):
        flash("Error: El archivo de registros no existe.", "error")
        return redirect(url_for('index'))
    return send_file(EXCEL_FILE, as_attachment=True, download_name="registros.xlsx")

@app.route("/submit", methods=["POST"])
def submit():
    """Procesa y guarda los datos del formulario."""
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
def consulta():
    """Muestra la página de búsqueda y los resultados."""
    query = request.args.get("query", "").strip().lower()
    
    if query:
        resultados = buscar_registros(query)
    else:
        resultados = None

    return render_template("consulta.html", resultados=resultados, headers=HEADERS)

# --- RUTA 'ACTUALIZAR_PAGO' COMPLETAMENTE MODIFICADA ---
@app.route("/actualizar_pago/<int:fila_idx>", methods=["GET", "POST"])
def actualizar_pago(fila_idx):
    """
    GET: Muestra un formulario para registrar un nuevo pago para un cliente existente.
    POST: Crea una nueva fila con los datos del cliente y el nuevo pago.
    """
    if request.method == "POST":
        # 1. Obtener los datos originales del cliente
        datos_originales = obtener_datos_fila(fila_idx)
        
        # 2. Obtener los nuevos datos de pago del formulario
        nuevos_datos_pago = request.form.to_dict()
        
        # 3. Combinar datos: mantener los originales y añadir los nuevos de pago
        nuevo_registro = datos_originales.copy()
        nuevo_registro.update(nuevos_datos_pago)
        
        # 4. Establecer la fecha de hoy para el nuevo pago
        nuevo_registro['fecha'] = datetime.now().strftime('%Y-%m-%d')
        
        # 5. Agregar la nueva fila como un registro completamente nuevo
        agregar_registro(nuevo_registro)
        
        flash("Nuevo pago registrado exitosamente como una nueva entrada.", "success")
        return redirect(url_for("consulta", query=request.args.get('query', '')))

    # Para el método GET: Muestra el formulario
    datos_actuales = obtener_datos_fila(fila_idx)
    query_original = request.args.get('query', '')
    return render_template("actualizar_pago.html", data=datos_actuales, fila_idx=fila_idx, query=query_original)


@app.route("/editar/<int:fila_idx>", methods=["GET", "POST"])
def editar(fila_idx):
    """Muestra el formulario para editar un registro completo."""
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
def eliminar():
    """Elimina una fila del archivo Excel."""
    fila_idx = int(request.form.get("fila_idx"))
    query = request.form.get("query", "")
    
    if eliminar_fila(fila_idx):
        flash("Registro eliminado correctamente.", "success")
    else:
        flash("Error: No se pudo eliminar el registro.", "error")
        
    return redirect(url_for("consulta", query=query))