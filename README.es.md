# DRF User Auth Example — Guía de la API

> ⚠️ **Aviso de datos ficticios:** todos los correos, contraseñas, nombres,
> números de identificación, teléfonos y UUID que aparecen en este README
> son **datos de ejemplo ficticios**, usados únicamente para ilustrar la
> forma de la solicitud/respuesta de cada endpoint. **No** son datos reales
> de usuario y ninguno debe tratarse como una credencial válida.

URL base usada en los ejemplos siguientes: `http://127.0.0.1:8000`

## Flujo de autenticación (resumen)

```
1. POST /v1/affiliate/providers/signup/   -> crea User + Provider, envía correo de verificación
2. (el usuario hace clic en el enlace del correo) -> GET /v1/auth/email-verify/<token>/ marca al usuario como verificado
3. POST /v1/auth/login/                   -> intercambia email/password por un JWT access + refresh
4. GET  /v1/affiliate/providers/          -> lista providers (necesita Authorization: Bearer <access>)
5. GET  /v1/affiliate/providers/<id>/     -> obtiene/actualiza un provider (necesita Authorization: Bearer <access>)
```

El token `access` devuelto por el login debe enviarse en cada solicitud protegida como:

```
Authorization: Bearer <access_token>
```

---

## 1. `POST /v1/affiliate/providers/signup/`

Registra un nuevo `User` junto con su perfil `Provider` relacionado.
Endpoint público (`AllowAny`) — no requiere token para llamarlo.

**Cuerpo de la solicitud (datos de ejemplo ficticios):**

```json
{
    "email": "dummy.provider@example.com",
    "password": "3243434",
    "provider": {
        "company": "3444",
        "fullname": "JOHN A SMITH",
        "id_type": 1,
        "id_number": "3434",
        "rnt": "343434",
        "address": "123 MAIN ST",
        "phone": "5555550123"
    }
}
```

**cURL:**

```bash
curl -X POST http://127.0.0.1:8000/v1/affiliate/providers/signup/ \
  -H "Content-Type: application/json" \
  -d '{
        "email": "dummy.provider@example.com",
        "password": "3243434",
        "provider": {
            "company": "3444",
            "fullname": "JOHN A SMITH",
            "id_type": 1,
            "id_number": "3434",
            "rnt": "343434",
            "address": "123 MAIN ST",
            "phone": "5555550123"
        }
      }'
```

**Respuesta exitosa `201 Created`:**

```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "User registered successfully"
}
```

Se envía en segundo plano un correo de verificación con un enlace como
`{{HOST_FRONT}}/provider/email-verify/<access_token>/`. La cuenta se crea
con `is_verified = False`, así que **aún no puede iniciar sesión** — el
par de tokens que devuelve este endpoint solo se usa para construir el
enlace de verificación, no como una sesión lista para usar.

**Posibles respuestas de error:**

- `400` — correo ya registrado: `{"error": "There is already a registered user with this email"}`
- `400` — error de validación (campo faltante/inválido): `{"error": "..."}`

---

## 2. `POST /v1/auth/login/`

Login estándar de SimpleJWT, extendido con los claims `role`/`email`/`initials`
en el payload del token y un campo `message` en el cuerpo de la respuesta.
El login se rechaza con `403` si el usuario aún no ha verificado su correo
(a menos que sea superusuario).

**Cuerpo de la solicitud (datos de ejemplo ficticios):**

```json
{
    "email": "dummy.provider@example.com",
    "password": "3243434"
}
```

**cURL:**

```bash
curl -X POST http://127.0.0.1:8000/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
        "email": "dummy.provider@example.com",
        "password": "3243434"
      }'
```

**Respuesta exitosa `200 OK`:**

```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "User login  successfully"
}
```

El token `access` decodificado incluye claims adicionales usados en la app:

```json
{
    "role": "user",
    "email": "dummy.provider@example.com",
    "initials": "JA"
}
```

**Posibles respuestas de error:**

- `401` — email/password incorrectos (error por defecto de SimpleJWT)
- `403` — `{"detail": "Email is not verified"}` si la cuenta aún no pasó
  por `GET /v1/auth/email-verify/<token>/`

Guarda el valor de `access` de esta respuesta — es el token que se usa en
el header `Authorization: Bearer <access>` en cada llamada siguiente.

---

## 3. `GET /v1/affiliate/providers/`

Lista los providers. Requiere un usuario autenticado **y verificado**
(`IsAuthenticated` + `IsVerified`). Los usuarios normales solo ven sus
propios provider(s); los superusuarios ven los de todos. Soporta un
filtro opcional `?company=` (parcial, sin distinguir mayúsculas/minúsculas)
y paginación.

**cURL:**

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/" \
  -H "Authorization: Bearer <access_token_from_login>"
```

Filtrando por company y paginando manualmente:

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/?company=3444&page=1&page_size=15" \
  -H "Authorization: Bearer <access_token_from_login>"
```

**Respuesta exitosa `200 OK`:**

```json
{
    "count": 1,
    "total_pages": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "6ab07505-975f-4d45-9293-11f8971fb1c7",
            "company": "3444",
            "fullname": "JOHN A SMITH",
            "id_type": 1,
            "id_number": "3434",
            "rnt": "343434",
            "address": "123 MAIN ST",
            "phone": "5555550123"
        }
    ]
}
```

**Posibles respuestas de error:**

- `401` — token ausente/inválido/expirado
- `403` — autenticado pero con `is_verified = False`

---

## 4. `GET /v1/affiliate/providers/<id>/`

Obtiene (o actualiza, vía `PUT`) un único provider por su UUID. Un usuario
solo puede acceder a su propio registro de provider; los superusuarios
pueden acceder a cualquier registro (validado por `has_permission`).

**cURL — obtener:**

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/6ab07505-975f-4d45-9293-11f8971fb1c7/" \
  -H "Authorization: Bearer <access_token_from_login>"
```

**Respuesta exitosa `200 OK`:**

```json
{
    "id": "6ab07505-975f-4d45-9293-11f8971fb1c7",
    "company": "3444",
    "fullname": "JOHN A SMITH",
    "id_type": 1,
    "id_number": "3434",
    "rnt": "343434",
    "address": "123 MAIN ST",
    "phone": "5555550123"
}
```

**cURL — actualizar (`PUT`, requiere el payload completo):**

```bash
curl -X PUT "http://127.0.0.1:8000/v1/affiliate/providers/6ab07505-975f-4d45-9293-11f8971fb1c7/" \
  -H "Authorization: Bearer <access_token_from_login>" \
  -H "Content-Type: application/json" \
  -d '{
        "company": "3444",
        "fullname": "JOHN A SMITH",
        "id_type": 1,
        "id_number": "3434",
        "rnt": "343434",
        "address": "NEW ADDRESS 123",
        "phone": "5555550123"
      }'
```

**Posibles respuestas de error:**

- `404` — `{"error": "Not found"}` cuando el UUID no existe
- `403` — intentar acceder/actualizar un provider que no es tuyo (y no
  eres superusuario)
- `400` — errores de validación en el `PUT`

---

## Flujo de ejemplo completo (encadenando las llamadas anteriores)

```bash
# 1) Registrar un provider ficticio
curl -X POST http://127.0.0.1:8000/v1/affiliate/providers/signup/ \
  -H "Content-Type: application/json" \
  -d '{
        "email": "dummy.provider@example.com",
        "password": "3243434",
        "provider": {
            "company": "3444",
            "fullname": "JOHN A SMITH",
            "id_type": 1,
            "id_number": "3434",
            "rnt": "343434",
            "address": "123 MAIN ST",
            "phone": "5555550123"
        }
      }'

# 2) Hacer clic en el enlace de verificación enviado a la dirección ficticia
#    (o llamar directamente a GET /v1/auth/email-verify/<access_token_from_step_1>/)

# 3) Iniciar sesión para obtener un par access/refresh utilizable
curl -X POST http://127.0.0.1:8000/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "dummy.provider@example.com", "password": "3243434"}'

# 4) Listar tu(s) propio(s) provider(s)
curl -X GET http://127.0.0.1:8000/v1/affiliate/providers/ \
  -H "Authorization: Bearer <access_token_from_step_3>"

# 5) Obtener un provider por id
curl -X GET http://127.0.0.1:8000/v1/affiliate/providers/6ab07505-975f-4d45-9293-11f8971fb1c7/ \
  -H "Authorization: Bearer <access_token_from_step_3>"
```
