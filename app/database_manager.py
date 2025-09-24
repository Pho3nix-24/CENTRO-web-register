import pandas as pd
import io
import mysql.connector
from mysql.connector import Error
from datetime import datetime

# --- CONFIGURACIÓN DE LA CONEXIÓN ---
db_config = {
    "host": "localhost",
    "database": "registro_app_db",
    "user": "root",
    "password": "pho3nix241236!",
}

def get_connection():
    """Crea y devuelve una nueva conexión a la base de datos."""
    return mysql.connector.connect(**db_config)

# --- FUNCIONES PARA MANEJAR CLIENTES Y PAGOS ---

def buscar_o_crear_cliente(data):
    """Busca un cliente por DNI. Si no existe, lo crea. Devuelve el ID del cliente."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql_buscar = "SELECT id FROM clientes WHERE dni = %s"
        cursor.execute(sql_buscar, (data.get('dni'),))
        cliente_existente = cursor.fetchone()
        
        if cliente_existente:
            return cliente_existente['id']
        else:
            sql_crear = """INSERT INTO clientes (nombre, dni, correo, celular, genero)
                           VALUES (%s, %s, %s, %s, %s)"""
            cliente_tuple = (
                data.get('cliente'), data.get('dni'), data.get('correo'),
                data.get('celular'), data.get('genero')
            )
            cursor.execute(sql_crear, cliente_tuple)
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        print(f"ERROR EN BD (buscar_o_crear_cliente): {e}")
        raise e
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def crear_pago(cliente_id, data):
    """Crea un nuevo registro de pago asociado a un cliente."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO pagos (cliente_id, fecha, cuota, tipo_de_cuota, banco, destino, 
                   numero_operacion, especialidad, modalidad, asesor)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        pago_tuple = (
            cliente_id,
            data.get('fecha'), data.get('cuota'), data.get('tipo_cuota'),
            data.get('banco'), data.get('destino'), data.get('numero_operacion'),
            data.get('especialidad'), data.get('modalidad'), data.get('asesor')
        )
        cursor.execute(sql, pago_tuple)
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"ERROR EN BD (crear_pago): {e}")
        raise e
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def buscar_pagos_completos(query):
    """Busca pagos y une la información del cliente."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT p.id, p.fecha, c.nombre, c.celular, p.especialidad, p.modalidad,
                   p.cuota, p.tipo_de_cuota, p.banco, p.destino, p.numero_operacion,
                   c.dni, c.correo, c.genero, p.asesor
            FROM pagos p JOIN clientes c ON p.cliente_id = c.id
            WHERE c.dni LIKE %s OR c.nombre LIKE %s
            ORDER BY p.id DESC
        """
        search_term = f"%{query}%"
        cursor.execute(sql, (search_term, search_term))
        return cursor.fetchall()
    except Error as e:
        print(f"ERROR EN BD (buscar_pagos_completos): {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def obtener_pago_por_id(pago_id):
    """Obtiene los datos de un pago específico y los del cliente asociado."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT p.*, c.nombre as cliente, c.dni, c.correo, c.celular, c.genero
            FROM pagos p JOIN clientes c ON p.cliente_id = c.id
            WHERE p.id = %s
        """
        cursor.execute(sql, (pago_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"ERROR EN BD (obtener_pago_por_id): {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def actualizar_pago(pago_id, form_data):
    """Actualiza un registro de PAGO existente."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        campos_pago = [
            "fecha", "cuota", "tipo_de_cuota", "banco", "destino",
            "numero_operacion", "especialidad", "modalidad", "asesor"
        ]
        set_clause = ", ".join([f"{campo} = %s" for campo in campos_pago])
        sql = f"UPDATE pagos SET {set_clause} WHERE id = %s"
        
        form_data_copy = form_data.copy()
        if 'num_operacion' in form_data_copy:
             form_data_copy['numero_operacion'] = form_data_copy.pop('num_operacion')

        valores = [form_data_copy.get(campo) for campo in campos_pago] + [pago_id]
        cursor.execute(sql, tuple(valores))
        conn.commit()
        return cursor.rowcount
    except Error as e:
        print(f"ERROR EN BD (actualizar_pago): {e}")
        raise e
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def eliminar_pago(pago_id):
    """Elimina un registro de PAGO específico."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM pagos WHERE id = %s"
        cursor.execute(sql, (pago_id,))
        conn.commit()
        return cursor.rowcount
    except Error as e:
        print(f"ERROR EN BD (eliminar_pago): {e}")
        raise e
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def generar_reporte_asesores_db(start_date_str=None, end_date_str=None):
    """Genera el reporte de asesores desde la tabla de pagos."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """SELECT asesor, COUNT(*) as registros_asesor, SUM(cuota) as total_asesor 
                 FROM pagos"""
        params, where_clauses = [], []
        if start_date_str:
            where_clauses.append("fecha >= %s")
            params.append(start_date_str)
        if end_date_str:
            where_clauses.append("fecha <= %s")
            params.append(end_date_str)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " GROUP BY asesor ORDER BY total_asesor DESC"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Error as e:
        print(f"ERROR EN BD (generar_reporte_asesores_db): {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def generar_excel_dinamico(headers):
    """Crea un archivo Excel en memoria formateando la fecha."""
    conn = None
    try:
        conn = get_connection()
        sql = """
            SELECT p.id, p.fecha, c.nombre, c.celular, p.especialidad, p.modalidad,
                   p.cuota, p.tipo_de_cuota, p.banco, p.destino, p.numero_operacion,
                   c.dni, c.correo, c.genero, p.asesor
            FROM pagos p JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.id DESC
        """
        df = pd.read_sql(sql, conn)
        df.columns = ["ID"] + headers
        
        # Formatea la columna de fecha para que no muestre la hora
        df['FECHA'] = pd.to_datetime(df['FECHA']).dt.strftime('%Y-%m-%d')
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Registros')
        output.seek(0)
        return output
    except Error as e:
        print(f"ERROR EN BD (generar_excel_dinamico): {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()
            
#Bitácora de auditoria de accesos
def registrar_auditoria(usuario, accion, ip, tabla=None, reg_id=None, detalles=None):
    """Inserta un nuevo registro en la tabla de auditoría."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO auditoria_accesos 
                   (timestamp, usuario_app, accion, tabla_afectada, registro_id, detalles, ip_origen)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        datos = (datetime.now(), usuario, accion, tabla, reg_id, detalles, ip)
        cursor.execute(sql, datos)
        conn.commit()
    except Error as e:
        # Mostrar en pantalla en caso falle la auditoria.
        print(f"ERROR CRÍTICO AL REGISTRAR AUDITORÍA: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
#Acceso a leer auditoria (ADMIN)   
def leer_log_auditoria():
    """Lee todos los registros de la tabla de auditoría."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM auditoria_accesos ORDER BY timestamp DESC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        print(f"ERROR EN BD (leer_log_auditoria): {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()