# Documentación de la API (APIFairy / OpenAPI)

La API REST se documenta con **APIFairy**, que genera la especificación
**OpenAPI 3.0** a partir de **schemas Marshmallow** y **decoradores**, y la
publica como **Swagger UI**.

| Recurso | URL |
|---------|-----|
| Swagger UI | `/docs` |
| OpenAPI JSON | `/openapi.json` |

---

## 1. Arquitectura de la documentación (Clean Architecture)

```
api/            ← Controladores: decoradores APIFairy + orquestación
schemas/        ← Contrato: serialización, validación y documentación (Marshmallow)
services/       ← Lógica de negocio (sin conocer HTTP)
```

- **`schemas/`** define el contrato → cada entidad es **un componente
  reutilizable** en OpenAPI (sin duplicación).
- **`api/`** sólo traduce HTTP ↔ servicios y se anota con APIFairy.
- **Auth Bearer** stateless: `services/token_service.py` (firma/verifica) +
  `api/security.py` (`HTTPTokenAuth` para `@authenticate`).

### Decoradores utilizados

| Decorador | Propósito |
|-----------|-----------|
| `@authenticate(token_auth)` | Exige token Bearer; documenta el `securityScheme` |
| `@arguments(QuerySchema)` | Valida y documenta **query params** |
| `@body(InputSchema)` | Valida y documenta el **request body** |
| `@response(OutputSchema)` | Serializa y documenta la **respuesta 200** |
| `@other_responses({...})` | Documenta **otros códigos** (400/401/404) y su body |

---

## 2. Autenticación

```
POST /api/tokens        # público — login
Authorization: Bearer <token>   # resto de endpoints
```

**Request** `POST /api/tokens`
```json
{ "username": "admin", "password": "Admin123*" }
```

**Response 200**
```json
{ "token": "eyJ1aWQiOjF9.<firma>", "token_type": "Bearer", "expires_in": 3600 }
```

En Swagger UI: **Authorize** → pega el token → ya puedes probar los endpoints.

---

## 3. Endpoints

**Autenticación**

| Método | Ruta | Auth | Body | Respuesta | Errores |
|--------|------|------|------|-----------|---------|
| POST | `/api/tokens` | — | `Login` | `Token` (200) | 400, 401 |

**Gastos**

| Método | Ruta | Auth | Body / Query / Path | Respuesta | Errores |
|--------|------|------|---------------------|-----------|---------|
| GET | `/api/expenses` | Bearer | `status?` | `ExpenseList` (200) | 401 |
| GET | `/api/expenses/{expense_id}` | Bearer | path | `ExpenseDetail` (200) | 401, 404 |
| POST | `/api/expenses` | Bearer | `ExpenseCreate` | `Expense` (201) | 400, 401, 422 |
| POST | `/api/expenses/{expense_id}/approve` | Bearer | path | `Expense` (200) | 401, 404, 409 |
| POST | `/api/expenses/{expense_id}/cancel` | Bearer | path | `Expense` (200) | 401, 404, 409 |

**Pagos**

| Método | Ruta | Auth | Body / Query / Path | Respuesta | Errores |
|--------|------|------|---------------------|-----------|---------|
| GET | `/api/payments` | Bearer | `status?`, `expense_id?` | `PaymentList` (200) | 401 |
| GET | `/api/payments/{payment_id}` | Bearer | path | `Payment` (200) | 401, 404 |
| POST | `/api/payments` | Bearer | `PaymentCreate` | `Payment` (201) | 400, 401, 404, 409 |
| POST | `/api/payments/{payment_id}/approve` | Bearer | path | `Payment` (200) | 401, 404, 409 |
| POST | `/api/payments/{payment_id}/pay` | Bearer | path | `Payment` (200) | 401, 404, 409 |
| POST | `/api/payments/{payment_id}/cancel` | Bearer | path | `Payment` (200) | 401, 404, 409 |

**Cuentas Bancarias**

| Método | Ruta | Auth | Body / Path | Respuesta | Errores |
|--------|------|------|-------------|-----------|---------|
| GET | `/api/bank-accounts` | Bearer | — | `BankAccountList` (200) | 401 |
| GET | `/api/bank-accounts/{account_id}` | Bearer | path | `BankAccountDetail` (200) | 401, 404 |
| POST | `/api/bank-accounts` | Bearer | `BankAccountCreate` | `BankAccount` (201) | 400, 401, 422 |

**Dashboard**

| Método | Ruta | Auth | Respuesta | Errores |
|--------|------|------|-----------|---------|
| GET | `/api/dashboard` | Bearer | `Dashboard` (200) | 401 |

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 400 | Validación de body/query fallida (`ValidationError`) |
| 401 | Token inválido o ausente (`Error`) |
| 404 | Recurso no encontrado (`Error`) |
| 409 | Regla de negocio violada (transición inválida) |
| 422 | Validación de dominio (monto inválido, etc.) |

---

## 4. Componentes (schemas) reutilizables

`Login`, `Token`, `Expense`, `ExpenseDetail`, `ExpenseList`, `Payment`,
`PaymentList`, `BankAccount`, `BankAccountDetail`, `BankAccountMovement`,
`BankAccountList`, `Dashboard`, `Kpis`, `Charts`, `Consumption`,
`AccountBalance`, `Error`, `ValidationError`.

`ExpenseDetail` extiende `Expense` (añade `payments`); `BankAccountDetail`
extiende `BankAccount` (añade `movements`) — **herencia de schemas** para evitar
duplicación.

---

## 5. Ejemplo de OpenAPI generado

`GET /api/expenses` (extracto de `/openapi.json`):

```json
{
  "summary": "Listar gastos.",
  "parameters": [
    {
      "in": "query", "name": "status", "required": false,
      "description": "Filtra por estado del gasto.",
      "schema": {
        "type": "string",
        "enum": ["PENDING", "APPROVED", "CANCELLED", "PAID"],
        "example": "APPROVED"
      }
    }
  ],
  "responses": {
    "200": { "content": { "application/json": {
        "schema": { "$ref": "#/components/schemas/ExpenseList" } } } },
    "401": { "description": "Token inválido o ausente.",
      "content": { "application/json": {
        "schema": { "$ref": "#/components/schemas/Error" } } } }
  },
  "security": [ { "token_auth": [] } ]
}
```

---

## 6. Mejoras de documentación aplicadas

- **Enmascarado del número de cuenta** en la respuesta (`******3210`) — evita
  exponer datos sensibles en la API.
- **`status` documentado como `enum`** (no string libre) en gastos y pagos.
- **Envelopes consistentes** `{count, data}` en todos los listados.
- **Tags en español** (Autenticación, Gastos, Pagos, Cuentas Bancarias,
  Dashboard) para una navegación clara en Swagger.
- **Auth Bearer en vez de sesión** para la API: documentable, probable desde
  Swagger y desacoplada de la UI web (que sigue usando sesión Flask-Login).
