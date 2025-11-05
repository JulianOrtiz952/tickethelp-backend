# Documentación: TTR Promedio y Flow Funnel

## 1. TTR Promedio (Tiempo Total de Resolución)

### Descripción
Endpoint que calcula el Tiempo Total de Resolución (TTR) promedio tanto a nivel global del sistema como por cada técnico. El TTR es el tiempo transcurrido desde la creación del ticket hasta su cierre (estado final).

### URLs

**Producción:**
```
https://tickethelp-backend.onrender.com/api/reports/stats/ttr-promedio/
```

**Local:**
```
http://localhost:8000/api/reports/stats/ttr-promedio/
```

### Método
`GET`

### Autenticación
Sí, requiere autenticación JWT.

### Permisos
Solo administradores pueden acceder a este endpoint.

### Headers
```json
{
  "Authorization": "Bearer <token_jwt>",
  "Content-Type": "application/json"
}
```

### Query Parameters
Ninguno.

### Request Body
No requiere body.

### Response JSON

**Estructura:**
```json
{
  "promedio_global": {
    "promedio_horas": 48.5,
    "promedio_dias": 2.02,
    "tickets_contemplados": 150
  },
  "por_tecnico": [
    {
      "tecnico_id": 1,
      "nombre_completo": "Juan Pérez",
      "promedio_horas": 24.5,
      "promedio_dias": 1.02,
      "tickets_contemplados": 45
    },
    {
      "tecnico_id": 2,
      "nombre_completo": "María García",
      "promedio_horas": 36.2,
      "promedio_dias": 1.51,
      "tickets_contemplados": 32
    }
  ]
}
```

**Campos:**
- `promedio_global`: Objeto con el TTR promedio de todo el sistema
  - `promedio_horas`: TTR promedio en horas (float, 2 decimales)
  - `promedio_dias`: TTR promedio en días (float, 2 decimales)
  - `tickets_contemplados`: Cantidad total de tickets finalizados considerados
- `por_tecnico`: Array de objetos con TTR promedio por técnico
  - `tecnico_id`: ID del técnico
  - `nombre_completo`: Nombre completo del técnico (o email si no tiene nombre)
  - `promedio_horas`: TTR promedio del técnico en horas
  - `promedio_dias`: TTR promedio del técnico en días
  - `tickets_contemplados`: Cantidad de tickets finalizados del técnico

**Nota:** Los técnicos están ordenados de menor a mayor TTR promedio (mejor rendimiento primero).

### Códigos de Respuesta

- `200 OK`: Solicitud exitosa
- `401 Unauthorized`: Token JWT inválido o ausente
- `403 Forbidden`: Usuario no es administrador
- `500 Internal Server Error`: Error interno del servidor

### Ejemplo con cURL

```bash
curl -X GET \
  "https://tickethelp-backend.onrender.com/api/reports/stats/ttr-promedio/" \
  -H "Authorization: Bearer <tu_token_jwt>" \
  -H "Content-Type: application/json"
```

### Ejemplo con fetch (JavaScript)

```javascript
fetch('https://tickethelp-backend.onrender.com/api/reports/stats/ttr-promedio/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer <tu_token_jwt>',
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('TTR Global:', data.promedio_global);
  console.log('TTR por Técnico:', data.por_tecnico);
})
.catch(error => console.error('Error:', error));
```

### Lógica de Cálculo

1. **TTR Global:**
   - Se consideran todos los tickets finalizados (estado_id=5)
   - Se calcula el tiempo desde `creado_en` hasta `resolved_at_final`
   - `resolved_at_final` = primera aprobación hacia estado final (si existe), o `actualizado_en` como respaldo
   - Se promedia el tiempo de todos los tickets finalizados

2. **TTR por Técnico:**
   - Para cada técnico que tiene tickets finalizados:
     - Se filtran sus tickets finalizados
     - Se calcula el TTR promedio de sus tickets
     - Se ordena de menor a mayor TTR (mejor rendimiento primero)

3. **Conversión de Tiempo:**
   - Horas: segundos / 3600
   - Días: segundos / 86400

---

## 2. Flow Funnel (Embudo de Flujo)

### Descripción
Endpoint que agrupa los tickets por estado intermedio (excluyendo "creado" y "finalizado") y retorna los totales ordenados según el flujo de proceso, incluyendo porcentajes basados en el total de tickets del sistema.

### URLs

**Producción:**
```
https://tickethelp-backend.onrender.com/api/reports/stats/flow-funnel/
```

**Local:**
```
http://localhost:8000/api/reports/stats/flow-funnel/
```

### Método
`GET`

### Autenticación
Sí, requiere autenticación JWT.

### Permisos
Solo administradores pueden acceder a este endpoint.

### Headers
```json
{
  "Authorization": "Bearer <token_jwt>",
  "Content-Type": "application/json"
}
```

### Query Parameters
Ninguno.

### Request Body
No requiere body.

### Response JSON

**Estructura:**
```json
[
  {
    "codigo": "diagnosis",
    "nombre": "En diagnóstico",
    "total": 25,
    "porcentaje": 12.5
  },
  {
    "codigo": "in_repair",
    "nombre": "En reparación",
    "total": 15,
    "porcentaje": 7.5
  },
  {
    "codigo": "testing",
    "nombre": "En prueba",
    "total": 10,
    "porcentaje": 5.0
  }
]
```

**Campos:**
- `codigo`: Código único del estado (string)
- `nombre`: Nombre legible del estado (string)
- `total`: Cantidad de tickets en ese estado (integer)
- `porcentaje`: Porcentaje del total de tickets del sistema (float, 2 decimales)

**Nota:** Los estados están ordenados según el flujo de proceso (orden de aparición en el sistema).

### Códigos de Respuesta

- `200 OK`: Solicitud exitosa
- `401 Unauthorized`: Token JWT inválido o ausente
- `403 Forbidden`: Usuario no es administrador
- `500 Internal Server Error`: Error interno del servidor

### Ejemplo con cURL

```bash
curl -X GET \
  "https://tickethelp-backend.onrender.com/api/reports/stats/flow-funnel/" \
  -H "Authorization: Bearer <tu_token_jwt>" \
  -H "Content-Type: application/json"
```

### Ejemplo con fetch (JavaScript)

```javascript
fetch('https://tickethelp-backend.onrender.com/api/reports/stats/flow-funnel/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer <tu_token_jwt>',
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Embudo de flujo:', data);
  data.forEach(estado => {
    console.log(`${estado.nombre}: ${estado.total} tickets (${estado.porcentaje}%)`);
  });
})
.catch(error => console.error('Error:', error));
```

### Lógica de Cálculo

1. **Estados Considerados:**
   - Se incluyen solo estados intermedios (excluyendo estado_id=1 "Abierto" y estado_id=5 "Finalizado")
   - Estados intermedios: "En diagnóstico" (id=2), "En reparación" (id=3), "En prueba" (id=4)

2. **Agrupación:**
   - Se agrupan los tickets por estado
   - Se cuenta el total de tickets en cada estado

3. **Porcentajes:**
   - Se calcula el porcentaje basado en el total de tickets del sistema (no solo los intermedios)
   - Fórmula: `(tickets_en_estado / total_tickets_sistema) * 100`

4. **Ordenamiento:**
   - Los estados se ordenan según su ID (flujo de proceso: diagnóstico → reparación → prueba)

---

## Estados del Sistema

Para referencia, los estados disponibles son:

- **ID 1**: "Abierto" (open) - Estado inicial
- **ID 2**: "En diagnóstico" (diagnosis) - Estado intermedio
- **ID 3**: "En reparación" (in_repair) - Estado intermedio
- **ID 4**: "En prueba" (testing) - Estado intermedio (requiere aprobación)
- **ID 5**: "Finalizado" (closed) - Estado final

