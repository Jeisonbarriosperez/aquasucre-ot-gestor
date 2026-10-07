from flask import Flask, request, redirect, url_for
import os
import psycopg2
from markupsafe import escape

app = Flask(__name__)

def obtener_conexion():
    return psycopg2.connect(os.environ["DATABASE_URL"])

@app.route("/")
def inicio():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                o.id_ot, o.id_pqr, o.tipo_servicio, o.descripcion,
                o.direccion, o.prioridad, o.estado, o.id_tecnico,
                t.nombre
            FROM ordenes_trabajo o
            LEFT JOIN tecnicos t ON t.id_tecnico = o.id_tecnico
            ORDER BY o.id_ot DESC
        """)
        ordenes = cursor.fetchall()

        filas_ordenes = ""
        for ot in ordenes:
            tecnico = ot[8] if ot[8] else "Sin asignar"
            estado = ot[6] if ot[6] else "Sin estado"

            if estado == "PENDIENTE":
                accion = f'<a href="/asignar/{ot[0]}">Asignar técnico</a>'
            elif estado == "ASIGNADA":
                accion = "Asignada"
            else:
                accion = "-"

            filas_ordenes += f"""
            <tr>
                <td>{escape(ot[0])}</td>
                <td>{escape(ot[1])}</td>
                <td>{escape(ot[2])}</td>
                <td>{escape(ot[3])}</td>
                <td>{escape(ot[4])}</td>
                <td>{escape(ot[5])}</td>
                <td>{escape(estado)}</td>
                <td>{escape(tecnico)}</td>
                <td>{accion}</td>
            </tr>
            """

        cursor.execute("""
            SELECT id_tecnico, nombre, telefono, especialidad, estado
            FROM tecnicos
            ORDER BY id_tecnico
        """)
        tecnicos = cursor.fetchall()

        filas_tecnicos = ""
        for tecnico in tecnicos:
            filas_tecnicos += f"""
            <tr>
                <td>{escape(tecnico[0])}</td>
                <td>{escape(tecnico[1])}</td>
                <td>{escape(tecnico[2])}</td>
                <td>{escape(tecnico[3])}</td>
                <td>{escape(tecnico[4])}</td>
            </tr>
            """

        cursor.close()
        conexion.close()

        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>AquaSucre OT</title>
        </head>
        <body>
            <h1>AquaSucre</h1>
            <h2>Gestión de Órdenes de Trabajo</h2>
            <p>Plataforma para la gestión y seguimiento de órdenes de trabajo.</p>
            <hr>

            <h2>Órdenes de Trabajo</h2>
            <table border="1" cellpadding="8">
                <tr>
                    <th>OT</th><th>PQR</th><th>Servicio</th><th>Descripción</th>
                    <th>Dirección</th><th>Prioridad</th><th>Estado</th>
                    <th>Técnico</th><th>Acción</th>
                </tr>
                {filas_ordenes}
            </table>

            <br><hr>
            <h2>Técnicos registrados</h2>
            <table border="1" cellpadding="8">
                <tr>
                    <th>ID</th><th>Nombre</th><th>Teléfono</th>
                    <th>Especialidad</th><th>Estado</th>
                </tr>
                {filas_tecnicos}
            </table>

            <br>
            <strong>AquaSucre OT - Versión 1.3</strong>
        </body>
        </html>
        """
    except Exception as error:
        return f"<h1>AquaSucre OT</h1><h2>Error conectando con la base de datos</h2><p>{escape(error)}</p>", 500

@app.route("/asignar/<int:id_ot>")
def asignar(id_ot):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_ot, id_pqr, tipo_servicio, descripcion,
                   direccion, prioridad, estado, id_tecnico
            FROM ordenes_trabajo
            WHERE id_ot = %s
        """, (id_ot,))
        ot = cursor.fetchone()

        if ot is None:
            cursor.close(); conexion.close()
            return "<h2>Orden de trabajo no encontrada</h2>", 404

        if ot[6] != "PENDIENTE":
            cursor.close(); conexion.close()
            return f"""
                <h2>La OT #{id_ot} no puede asignarse</h2>
                <p>Estado actual: {escape(ot[6])}</p>
                <a href="/">Volver al Gestor de OT</a>
            """, 409

        cursor.execute("""
            SELECT id_tecnico, nombre, especialidad
            FROM tecnicos
            WHERE UPPER(estado) = 'ACTIVO'
            ORDER BY nombre
        """)
        tecnicos = cursor.fetchall()
        cursor.close()
        conexion.close()

        opciones = "".join(
            f'<option value="{t[0]}">{escape(t[1])} - {escape(t[2])}</option>'
            for t in tecnicos
        )

        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Asignar OT - AquaSucre</title></head>
        <body>
            <h1>AquaSucre</h1>
            <h2>Asignar Orden de Trabajo</h2>
            <hr>
            <h3>OT #{ot[0]}</h3>
            <p><strong>PQR:</strong> {escape(ot[1])}</p>
            <p><strong>Servicio:</strong> {escape(ot[2])}</p>
            <p><strong>Descripción:</strong> {escape(ot[3])}</p>
            <p><strong>Dirección:</strong> {escape(ot[4])}</p>
            <p><strong>Prioridad:</strong> {escape(ot[5])}</p>
            <p><strong>Estado:</strong> {escape(ot[6])}</p>
            <hr>
            <h3>Seleccionar técnico</h3>
            <form method="POST" action="/confirmar-asignacion/{ot[0]}">
                <select name="id_tecnico" required>
                    <option value="">-- Seleccione un técnico --</option>
                    {opciones}
                </select>
                <br><br>
                <button type="submit">Confirmar asignación</button>
            </form>
            <br><a href="/">Volver al Gestor de OT</a>
        </body>
        </html>
        """
    except Exception as error:
        return f"<h2>Error consultando la orden de trabajo</h2><p>{escape(error)}</p>", 500

@app.route("/confirmar-asignacion/<int:id_ot>", methods=["POST"])
def confirmar_asignacion(id_ot):
    id_tecnico = request.form.get("id_tecnico", "").strip()
    if not id_tecnico.isdigit():
        return "<h2>Técnico no válido</h2><a href='/'>Volver</a>", 400

    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Validar que el técnico exista y esté activo.
        cursor.execute("""
            SELECT nombre
            FROM tecnicos
            WHERE id_tecnico = %s AND UPPER(estado) = 'ACTIVO'
        """, (int(id_tecnico),))
        tecnico = cursor.fetchone()
        if tecnico is None:
            conexion.rollback()
            cursor.close(); conexion.close()
            return "<h2>El técnico seleccionado no existe o no está activo.</h2><a href='/'>Volver</a>", 400

        # Actualización protegida: solo se asigna si sigue PENDIENTE.
        cursor.execute("""
            UPDATE ordenes_trabajo
            SET id_tecnico = %s,
                estado = 'ASIGNADA',
                fecha_asignacion = CURRENT_TIMESTAMP
            WHERE id_ot = %s
              AND estado = 'PENDIENTE'
            RETURNING id_ot
        """, (int(id_tecnico), id_ot))

        actualizado = cursor.fetchone()
        if actualizado is None:
            conexion.rollback()
            cursor.close(); conexion.close()
            return f"""
                <h2>No se realizó la asignación</h2>
                <p>La OT #{id_ot} ya no está en estado PENDIENTE.</p>
                <a href="/">Volver al Gestor de OT</a>
            """, 409

        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("inicio"))

    except Exception as error:
        if conexion:
            conexion.rollback()
            conexion.close()
        return f"<h2>Error realizando la asignación</h2><p>{escape(error)}</p><a href='/'>Volver</a>", 500

if __name__ == "__main__":
    app.run()
