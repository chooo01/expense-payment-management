# 💰 ExpensePay — Sistema de Gestión de Gastos y Pagos Empresariales

Aplicación web para **registrar, aprobar, cancelar y pagar gastos** de una
empresa, manteniendo el control sobre las cuentas bancarias y el flujo
financiero, con **auditoría completa** de cada cambio de estado.

> Entrega de prueba técnica
> Stack: **Python · Flask · SQLAlchemy · PostgreSQL · Bootstrap 5 · Chart.js**.

---

## 📑 Tabla de contenido

1. [Características](#-características)
2. [Stack y justificación](#-stack-tecnológico-y-justificación)
3. [Arquitectura por capas](#-arquitectura-por-capas)
4. [Modelo de datos](#-modelo-de-datos)
5. [Reglas de negocio](#-reglas-de-negocio)
6. [API REST](#-api-rest)
7. [Autenticación](#-autenticación)
8. [Dashboard](#-dashboard)
9. [Calidad profesional](#-calidad-profesional)
10. [Puesta en marcha local](#-puesta-en-marcha-local)
11. [Pruebas](#-pruebas)
12. [Despliegue en Render](#-despliegue-en-render)
13. [Variables de entorno](#-variables-de-entorno)
14. [Casos de prueba sugeridos](#-casos-de-prueba-sugeridos)

---

## ✨ Características

- CRUD de **gastos** con ciclo de aprobación y cancelación.
- Generación de **pagos** desde gastos aprobados, con **pagos parciales** y
  prevención de **pagos duplicados**.
- **Cuentas bancarias** con validación de saldo y **ledger de movimientos**.
- **Auditoría** inmutable de todas las transiciones de estado.
- **Dashboard ejecutivo** con KPIs y 4 gráficas (Chart.js).
- **API REST** documentada (solo lectura) para integración.
- **Autenticación** por sesión con contraseñas **bcrypt**.
- **Soft delete**, manejo centralizado de errores y logging estructurado.

---

## 🧰 Stack tecnológico y justificación

| Componente | Elección | Justificación |
|------------|----------|---------------|
| Lenguaje | Python 3.11 | Pedido por la prueba; ecosistema maduro |
| Framework | **Flask 3** | Microframework flexible; permite arquitectura por capas explícita sin imponer estructura |
| ORM | **SQLAlchemy 2 / Flask-SQLAlchemy** | Estándar de facto; tipado declarativo, portable entre PostgreSQL y SQLite |
| BD | **PostgreSQL** (prod) / SQLite (dev/test) | Postgres por robustez transaccional; SQLite para arranque inmediato y tests rápidos en memoria |
| Migraciones | **Flask-Migrate (Alembic)** | Versionado de esquema reproducible |
| Auth | **Flask-Login + Flask-Bcrypt** | Sesiones server-side simples; bcrypt para hashing seguro (pedido explícito) |
| Frontend | **Bootstrap 5 + Bootstrap Icons** | UI administrativa responsiva sin build step |
| Gráficas | **Chart.js 4** | Ligero, alimentado por el endpoint `/api/dashboard` |
| Servidor prod | **Gunicorn** | WSGI estándar para Render |
| Tests | **pytest** | Conciso, fixtures potentes |

**Decisiones clave:**

- **`Decimal`/`NUMERIC(18,2)` para dinero**, nunca `float` — evita errores de
  redondeo en montos y saldos.
- **El saldo de la cuenta solo se mueve en la capa de servicio** y siempre
  acompañado de un registro en el ledger; balance y movimientos no pueden
  divergir.
- **Las máquinas de estado viven en los servicios**, no en las rutas ni en los
  modelos: una sola fuente de verdad, fácil de testear.

---

## 🏛 Arquitectura por capas

```
expense-payment-management/
├── app.py              # Application factory + CLI (init-db, seed) + healthcheck
├── wsgi.py             # Entry point para gunicorn (producción)
├── config/             # Configuración por entorno (dev/test/prod)
├── database/           # Instancia SQLAlchemy/Migrate + seed de datos
├── models/             # Entidades ORM + enums + mixins (timestamps, soft delete)
├── repositories/       # Acceso a datos (queries) — aísla el ORM
├── services/           # Lógica de negocio, reglas, máquinas de estado, transacciones
├── routes/             # Controladores web (render de templates, formularios)
├── api/                # Controladores REST (JSON, solo lectura)
├── middleware/         # Manejo de errores + logging de requests
├── auth/               # Flask-Login (user loader, guardas, redirecciones)
├── templates/          # Vistas Jinja2 (Bootstrap)
├── static/             # CSS y JS (dashboard / Chart.js)
├── tests/              # Suite pytest
└── docs/               # Diseño funcional (Mermaid) y de base de datos
```

### Responsabilidad de cada capa

| Carpeta | Responsabilidad | Regla de dependencia |
|---------|-----------------|----------------------|
| `config/` | Resolver configuración según `FLASK_ENV`; secretos, BD, logging | No depende de nada |
| `database/` | Singletons `db`/`migrate` y seeding | Base para modelos |
| `models/` | Mapear tablas, enums de estado, helpers de dominio (`remaining_amount`) | Depende solo de `database` |
| `repositories/` | Encapsular consultas; ocultar el `session` del ORM; filtrar soft-delete | Depende de `models` |
| `services/` | **Corazón del negocio**: validaciones, máquinas de estado, transacciones atómicas, auditoría | Depende de `repositories` |
| `routes/` | Traducir HTTP↔servicios para vistas HTML; flash messages | Depende de `services` |
| `api/` | Igual que `routes` pero responde JSON; documentación de endpoints | Depende de `services` |
| `middleware/` | Errores (→ JSON o flash) y logging por request; `rollback` ante fallo | Transversal |
| `auth/` | Sesión, `user_loader`, manejo de no autenticado (401 JSON vs redirect) | Transversal |

**Flujo de una petición** (ejecutar un pago):

```
Browser/API → routes|api → services (regla + transacción)
            → repositories → models → DB
            ↳ middleware (logging, errores, rollback)
```

El diseño en capas hace que la lógica sea **testeable sin HTTP** (los tests
llaman directamente a los servicios) y que cambiar de PostgreSQL a otro motor,
o de Flask a otro framework, afecte solo a las capas externas.

Diagramas detallados en [`docs/01-functional-design.md`](docs/01-functional-design.md).

---

## 🗄 Modelo de datos

Diagrama ER, cardinalidades, llaves e índices en
[`docs/02-database-design.md`](docs/02-database-design.md).

Tablas: `users`, `bank_accounts`, `expenses`, `payments`, `status_history` y
`bank_account_movements` (ledger; añadido para cumplir *"mantener historial de
movimientos"*).

---

## ⚖️ Reglas de negocio

### Gastos
- Inicia en **PENDIENTE**.
- **PENDIENTE → APROBADO**; **PENDIENTE/APROBADO → CANCELADO**.
- Un gasto **CANCELADO nunca se reactiva** (estado terminal).
- Un gasto **APROBADO** puede generar pagos.
- Pasa a **PAGADO** automáticamente cuando sus pagos cubren el total.

### Pagos
- Se originan **solo desde un gasto APROBADO**.
- Se generan con el botón **"Generar Pago"**.
- Soportan **pagos parciales**; `Σ(pagos no cancelados) ≤ monto del gasto`
  (evita duplicados/sobrepago).
- Pueden **aprobarse, cancelarse y marcarse como pagados**.

### Cuentas bancarias
- Un pago **no puede exceder el saldo disponible**.
- Al **ejecutar** un pago se **disminuye el saldo** y se registra el movimiento.
- Cancelar un pago **ya ejecutado** revierte el saldo (movimiento `CREDIT`) y
  reabre el gasto.

> Implementación: `services/expense_service.py`, `services/payment_service.py`,
> `services/bank_account_service.py`. Las transiciones inválidas lanzan
> `BusinessRuleError` (HTTP 409).

---

## 🔌 API REST

Todos los endpoints son **GET** (solo lectura), requieren **sesión
autenticada** y responden JSON. Sin sesión → `401 {"error": ...}`.

### Gastos

```
GET /api/expenses                # lista (?status=PENDING|APPROVED|CANCELLED|PAID)
GET /api/expenses/{id}           # detalle + pagos
```

`GET /api/expenses` →
```json
{
  "count": 2,
  "data": [
    {
      "id": 1, "folio": "EXP-2026-000001",
      "description": "Compra de equipos de cómputo",
      "amount": 25000.00, "paid_amount": 25000.00, "remaining_amount": 0.00,
      "status": "PAID", "status_label": "Pagado",
      "created_by": 1, "approved_by": 1,
      "created_at": "2026-06-15T12:00:00+00:00",
      "updated_at": "2026-06-15T13:00:00+00:00"
    }
  ]
}
```

### Pagos

```
GET /api/payments                # (?status=... &expense_id=...)
GET /api/payments/{id}
```

`GET /api/payments/1` →
```json
{
  "id": 1, "payment_folio": "PAY-2026-000001",
  "expense_id": 1, "expense_folio": "EXP-2026-000001",
  "bank_account_id": 2, "bank_account_name": "Cuenta Operativa",
  "amount": 25000.00, "status": "PAID", "status_label": "Pagado",
  "payment_date": "2026-06-15T13:00:00+00:00",
  "created_at": "2026-06-15T12:45:00+00:00"
}
```

### Cuentas bancarias

```
GET /api/bank-accounts
GET /api/bank-accounts/{id}      # incluye movimientos del ledger
```

`GET /api/bank-accounts/2` →
```json
{
  "id": 2, "account_name": "Cuenta Operativa", "bank_name": "BBVA",
  "account_number": "******3210", "current_balance": 75000.00, "active": true,
  "movements": [
    {
      "id": 1, "movement_type": "DEBIT", "amount": 25000.00,
      "balance_after": 75000.00,
      "description": "Pago PAY-2026-000001 (gasto EXP-2026-000001)",
      "created_at": "2026-06-15T13:00:00+00:00"
    }
  ]
}
```

### Dashboard

```
GET /api/dashboard
```

```json
{
  "kpis": {
    "total_expenses": 103000.00,
    "total_paid": 40000.00,
    "pending_expenses": 1,
    "pending_payments": 1,
    "available_balance": 310000.00
  },
  "charts": {
    "expenses_by_month": [["2026-01", 0.0], ["2026-06", 103000.0]],
    "payments_by_month":  [["2026-01", 0.0], ["2026-06", 40000.0]],
    "expenses_by_status": {"APPROVED": 1, "CANCELLED": 1, "PAID": 1, "PENDING": 1},
    "payments_by_status": {"PAID": 2, "PENDING": 1},
    "consumption_by_account": [
      {"account_id": 2, "account_name": "Cuenta Operativa", "total": 25000.0}
    ]
  },
  "bank_accounts": [
    {"id": 1, "account_name": "Cuenta Nómina", "bank_name": "Santander",
     "current_balance": 235000.0}
  ]
}
```

| Campo del dashboard | Significado |
|---------------------|-------------|
| `total_expenses` | Suma de todos los gastos no eliminados |
| `total_paid` | Suma de pagos ejecutados (PAGADO) |
| `pending_expenses` | Conteo de gastos en estado PENDIENTE |
| `pending_payments` | Conteo de pagos en estado PENDIENTE |
| `available_balance` | Saldo agregado de las cuentas activas |

---

## 🔐 Autenticación

- Login usuario/contraseña con **Flask-Login** (sesión firmada).
- Contraseñas hasheadas con **bcrypt** (`Flask-Bcrypt`); el texto plano nunca
  se persiste.
- Rutas protegidas con `@login_required`; las de `/api/*` devuelven `401 JSON`,
  las web redirigen al login (con `next` seguro contra open-redirect).
- **Logout** vía POST (evita CSRF por GET).
- **No hay registro público**: los usuarios se crean por seed/CLI (requisito).

---

## 📊 Dashboard

- **KPIs**: Gastos Totales, Pagos Totales, Gastos Pendientes, Pagos Pendientes,
  Saldo Disponible.
- **Gráficas (Chart.js)**: Gastos vs. Pagos por mes, Distribución de gastos por
  estado, Pagos por estado, Consumo por cuenta bancaria.
- Las gráficas consumen `GET /api/dashboard`, por lo que la UI y la API
  comparten exactamente los mismos números.

---

## 🛡 Calidad profesional

| Requisito | Cómo se cumple |
|-----------|----------------|
| Manejo de errores | `middleware/error_handlers.py` (JSON o flash) + `rollback` |
| Validaciones | En servicios (`ValidationError`/`BusinessRuleError`) y en formularios HTML |
| Logs | `middleware/logging_middleware.py` (un log por request con usuario/latencia) |
| Soft Delete | `SoftDeleteMixin` + filtrado por defecto en repositorios |
| Auditoría | Tabla `status_history` (append-only) en cada transición |
| Comentarios de arquitectura | Docstrings por módulo explicando el "por qué" |
| Casos de prueba | Suite `tests/` + sección de casos sugeridos |
| Atomicidad | El servicio posee la transacción; commit/rollback únicos |

---

## 🚀 Puesta en marcha local

Requisitos: Python 3.11+.

```bash
# 1) Entorno virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2) Dependencias
pip install -r requirements.txt

# 3) Variables de entorno
cp .env.example .env          # (Windows: copy .env.example .env)
#   Sin DATABASE_URL usa SQLite local automáticamente.

# 4) Crear esquema + datos demo (usuario admin incluido)
flask --app app seed

# 5) Ejecutar
flask --app app run --debug
#   → http://127.0.0.1:5000   (login: admin / Admin123*)
```

> Comandos CLI: `flask --app app init-db` (solo tablas) y
> `flask --app app seed` (tablas + admin + datos demo).

---

## ✅ Pruebas

```bash
pytest                 # ejecuta toda la suite
pytest --cov=. --cov-report=term-missing   # con cobertura
```

La suite cubre la **máquina de estados de gastos y pagos**, el **impacto en el
saldo**, la **prevención de sobrepago**, la **reversa de pagos**, el **guard de
autenticación** y la **forma de las respuestas de la API**.

---

## ☁️ Despliegue en Render

El repositorio incluye [`render.yaml`](render.yaml) (Blueprint) que provisiona
un **Web Service gratuito** + **PostgreSQL gratuito**:

1. Sube el repo a GitHub.
2. En Render: **New → Blueprint** y selecciona el repositorio.
3. Render lee `render.yaml`:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn wsgi:app --workers 2 --timeout 60`
   - `DATABASE_URL` se inyecta desde la BD administrada.
   - `SECRET_KEY` se genera automáticamente.
   - Define `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` en el dashboard.
4. `wsgi.py` ejecuta `create_all()` en el primer arranque (idempotente).
5. (Opcional) Ejecuta el seed una vez desde la *Shell* de Render:
   `flask --app app seed`.
6. Healthcheck en `/healthz`.

> En un entorno productivo maduro se usaría `flask db upgrade` (Alembic) en el
> `buildCommand` en lugar de `create_all`. Se deja `create_all` para que el
> demo despliegue sin pasos manuales.

---

## 🔧 Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `FLASK_ENV` | `development` / `testing` / `production` | `development` |
| `SECRET_KEY` | Firma de la sesión (obligatoria en prod) | inseguro (solo dev) |
| `DATABASE_URL` | Cadena PostgreSQL; vacío → SQLite local | SQLite |
| `SEED_ADMIN_USERNAME` | Usuario admin inicial | `admin` |
| `SEED_ADMIN_PASSWORD` | Contraseña admin inicial | `Admin123*` |
| `LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` |

---

## 🧪 Casos de prueba sugeridos

**Gastos**
1. Crear gasto → estado PENDIENTE y folio `EXP-AAAA-NNNNNN`.
2. Aprobar PENDIENTE → APROBADO; reaprobar debe fallar (409).
3. Cancelar → CANCELADO; aprobar un cancelado debe fallar (no reactivable).
4. Monto ≤ 0 o no numérico → 422.
5. Cancelar gasto con pagos activos → 409.

**Pagos**
6. Generar pago de gasto no aprobado → 409.
7. Generar pago > saldo pendiente del gasto → 409 (anti-duplicado).
8. Dos pagos parciales que suman el total → gasto pasa a PAGADO.
9. Ejecutar pago con saldo insuficiente → 409, saldo intacto.
10. Ejecutar pago aprobado → débito + movimiento DEBIT + `payment_date`.
11. Cancelar pago ejecutado → crédito de reversa + gasto reabierto a APROBADO.

**Cuentas / API / Auth**
12. `GET /api/*` sin sesión → 401 JSON.
13. `GET /api/dashboard` → claves `kpis`, `charts`, `bank_accounts`.
14. `GET /api/expenses?status=BOGUS` → 422.
15. `GET /api/expenses/999` → 404 JSON.

Las pruebas 1–13 están automatizadas en `tests/`.

---

### Autor

Entrega para prueba técnica — arquitectura, código y documentación.
