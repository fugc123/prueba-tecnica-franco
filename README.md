# Prueba tecnica franco

Api en fastapi con postgresql para registrar clientes y evaluar operaciones mediante un motor de reglas.

## Como levantar el proyecto

Con docker y docker compose instalados, correr en la raiz del proyecto:

```bash
docker compose up --build
```

La api queda corriendo en `http://localhost:8000` y la documentacion de swagger en `http://localhost:8000/docs`.

Al levantar se cargan algunos datos de prueba automaticamente para poder probar directo:
- Cliente low risk: `1e7dc657-96ef-454e-b3db-05acfe5ec34c` (Juan perez)
- Cliente medium risk: `2b8ed768-07fa-465f-a4ec-16bd0f6fd45d` (Maria gomez)
- Cliente high risk: `3c9fe879-18ab-476a-b5fd-27ce1a7ae56e` (Carlos lopez)

## Autenticacion

Se uso autenticacion con jwt bearer tokens. Todos los endpoints estan protegidos salvo el de login.

Para probar desde swagger (`/docs`):
1. Ir al endpoint `POST /auth/login` y ejecutarlo con el usuario de prueba que ya viene cargado (`username`: `admin`, `password`: `admin123`).
2. Copiar el `access_token` que devuelve.
3. Pegar ese token en el boton `Authorize` de arriba a la derecha o directamente en el campo `Bearer-Token` de cada endpoint.

Si se prueba por consola o postman, hay que mandar el header `Authorization: Bearer <token>`.

## Tests

Para correr los tests con el contenedor levantado:

```bash
docker compose exec api pytest -v
```

O localmente desde un entorno virtual:

```bash
pip install -r requirements.txt
pytest -v
```

## Trazabilidad

Cada operacion que se evalua guarda un registro en la tabla `decision_audit_logs` con las reglas que se corrieron, cuales se activaron y el estado final. Se puede consultar desde el endpoint `GET /audit-logs`.

## Preguntas abiertas

### A) Manejo de multiples monedas, reglas por currency y conversion de montos

Para manejar varias monedas, la idea es convertir el monto a usd antes de pasarle los datos al motor de reglas, guardando en el contexto tanto el monto original con su moneda como el monto convertido (`amount_in_usd`). Hoy esa conversion esta en una funcion `convert_to_usd` dentro de `app/application/services.py`, que en un caso real consultaria un servicio de cotizaciones o una tabla de tipos de cambio.

Componentes a modificar:
- `app/application/services.py`: cambiar el diccionario fijo de tasas por un cliente o tabla que traiga la cotizacion actual.
- `app/domain/rules.py`: agregar la nueva clase de regla que valide la moneda puntual mirando `context.operation.currency` y sumarla a la lista en `get_default_rules()`.

Decisiones de diseno que facilitan agregar reglas:
- Como el contexto de evaluacion ya tiene `amount_in_usd` y tambien los datos originales de la operacion, las reglas actuales siguen funcionando en usd sin tocarlas y cualquier regla nueva por moneda se agrega como una clase mas sin cambiar el motor.

### B) Nuevos campos en la entidad operacion y extension del motor de reglas

Si la operacion empieza a recibir campos nuevos como pais de destino, canal o ip, esos datos se pasan dentro de `OperationCandidate` (que ademas ya tiene un diccionario `metadata` para datos extra) y llegan a todas las reglas a traves del contexto de evaluacion.

Componentes a modificar:
- `app/api/schemas.py` y `app/infrastructure/models.py`: agregar los campos nuevos en el request y response de fastapi y en el modelo de base de datos si hace falta guardarlos.
- `app/domain/entities.py`: sumar el campo en `OperationCandidate` o pasarlo en `metadata`.
- `app/domain/rules.py`: crear la nueva regla heredando de `BusinessRule` y agregarla en `get_default_rules()`.

Decisiones de diseno que facilitan agregar reglas:
- Cada regla es una clase independiente que implementa `evaluate(context)` y devuelve un resultado. El motor solo recorre la lista de reglas registradas y define el estado final segun prioridad. Gracias a que todas reciben el mismo objeto de contexto, sumar campos o reglas nuevas no obliga a cambiar la firma de los metodos ni la logica del motor.
