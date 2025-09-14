import os
from openpyxl import Workbook, load_workbook
from datetime import datetime, date

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EXCEL_FILE = os.path.join(BASE_DIR, "registros.xlsx")

HEADERS = [
    "FECHA", "CLIENTE", "CELULAR", "ESPECIALIDAD", "MODALIDAD",
    "CUOTA", "TIPO DE CUOTA", "BANCO", "DESTINO", "N° OPERACIÓN",
    "DNI", "CORREO", "GÉNERO", "ASESOR",
]

FIELDS = [
    "fecha", "cliente", "celular", "especialidad", "modalidad",
    "cuota", "tipo_cuota", "banco", "destino", "num_operacion",
    "dni", "correo", "genero", "asesor",
]

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.append(HEADERS)
        wb.save(EXCEL_FILE)

def agregar_registro(data: dict):
    init_excel()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    fila = [data.get(f, "") for f in FIELDS]
    ws.append(fila)
    wb.save(EXCEL_FILE)

def verificar_duplicado(dni_nuevo, num_operacion_nuevo):
    if not os.path.exists(EXCEL_FILE):
        return None
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    dni_col_idx = FIELDS.index("dni")
    op_col_idx = FIELDS.index("num_operacion")
    for row in ws.iter_rows(min_row=2, values_only=True):
        if len(row) <= max(dni_col_idx, op_col_idx):
            continue
        dni_existente = str(row[dni_col_idx] or "").strip()
        num_op_existente = str(row[op_col_idx] or "").strip()
        if dni_existente == dni_nuevo:
            return f"Error: El DNI '{dni_nuevo}' ya se encuentra registrado."
        if num_operacion_nuevo and num_op_existente == num_operacion_nuevo:
            return f"Error: El N° de Operación '{num_operacion_nuevo}' ya se encuentra registrado."
    return None

def buscar_registros(query):
    resultados = []
    if not query or not os.path.exists(EXCEL_FILE):
        return resultados
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    for idx, row in enumerate(ws.iter_rows(min_row=2, max_col=len(HEADERS), values_only=True), start=2):
        dni = str(row[FIELDS.index("dni")] or "").lower()
        cliente = str(row[FIELDS.index("cliente")] or "").lower()
        if query in dni or query in cliente:
            resultados.append((row, idx))
    return resultados

def obtener_datos_fila(fila_idx):
    """Obtiene los datos de una fila específica para la edición."""
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    fila_valores = [ws.cell(row=fila_idx, column=col).value for col in range(1, len(FIELDS) + 1)]
    
    # --- ESTA LÍNEA ESTABA INCORRECTA Y HA SIDO CORREGIDA ---
    data = {field: _format_cell_value(val) for field, val in zip(FIELDS, fila_valores)}
    return data

def actualizar_fila(fila_idx, form_data):
    init_excel()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    for col_idx, field in enumerate(FIELDS, start=1):
        valor = form_data.get(field, "")
        ws.cell(row=fila_idx, column=col_idx).value = valor
    wb.save(EXCEL_FILE)

def eliminar_fila(fila_idx):
    """Elimina una fila por su índice."""
    try:
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        ws.delete_rows(fila_idx)
        wb.save(EXCEL_FILE)
        return True
    except Exception:
        return False

def _format_cell_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value)