# AquaSucre OT - Versión 1.3

Mantiene el Gestor OT existente y completa la asignación de técnicos.

Cambios:
- Muestra el nombre del técnico mediante LEFT JOIN.
- Agrega la columna Acción.
- Solo permite asignar OT en estado PENDIENTE.
- Agrega POST /confirmar-asignacion/<id_ot>.
- Al asignar: id_tecnico, estado=ASIGNADA y fecha_asignacion=CURRENT_TIMESTAMP.
- Valida que el técnico esté ACTIVO.
