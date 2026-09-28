# DRF User Auth Example — API Guide

> ⚠️ **Fake data disclaimer:** every email, password, name, ID number, phone
> number and UUID shown in this README is **dummy example data**, used only
> to illustrate the request/response shape of each endpoint. It is **not**
> real user data and none of it should be treated as a valid credential.

Base URL used in the examples below: `http://127.0.0.1:8000`

## Auth flow overview

```
1. POST /v1/affiliate/providers/signup/   -> creates User + Provider, sends verification email
2. (user clicks the link in the email)    -> GET /v1/auth/email-verify/<token>/ marks the user as verified
3. POST /v1/auth/login/                   -> exchanges email/password for access + refresh JWT
4. GET  /v1/affiliate/providers/          -> list providers (needs Authorization: Bearer <access>)
5. GET  /v1/affiliate/providers/<id>/     -> retrieve/update a single provider (needs Authorization: Bearer <access>)
```

The `access` token returned by login must be sent on every protected request as:

```
Authorization: Bearer <access_token>
```

---

## 1. `POST /v1/affiliate/providers/signup/`

Registers a new `User` + its related `Provider` profile. Public endpoint
(`AllowAny`) — no token required to call it.

**Request body (fake example data):**

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

**Success response `201 Created`:**

```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "User registered successfully"
}
```

A verification email is sent in the background with a link like
`{{HOST_FRONT}}/provider/email-verify/<access_token>/`. The account is
created with `is_verified = False`, so it **cannot log in yet** — the
token pair returned here is only used to build the verification link, not
as a ready-to-use session.

**Possible error responses:**

- `400` — email already registered: `{"error": "There is already a registered user with this email"}`
- `400` — validation error (missing/invalid field): `{"error": "..."}`

---

## 2. `POST /v1/auth/login/`

Standard SimpleJWT login, extended with a `role`/`email`/`initials` claim
in the token payload and a `message` field in the response body.
Login is rejected with `403` if the user hasn't verified their email yet
(unless they're a superuser).

**Request body (fake example data):**

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

**Success response `200 OK`:**

```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "User login  successfully"
}
```

The decoded `access` token carries extra claims used across the app:

```json
{
    "role": "user",
    "email": "dummy.provider@example.com",
    "initials": "JA"
}
```

**Possible error responses:**

- `401` — wrong email/password (default SimpleJWT error)
- `403` — `{"detail": "Email is not verified"}` if the account hasn't gone
  through `GET /v1/auth/email-verify/<token>/` yet

Save the `access` value from this response — it's the token used in the
`Authorization: Bearer <access>` header for every call below.

---

## 3. `GET /v1/affiliate/providers/`

Lists providers. Requires an authenticated **and verified** user
(`IsAuthenticated` + `IsVerified`). Regular users only see their own
provider(s); superusers see everyone's. Supports an optional
`?company=` filter (case-insensitive, partial match) and pagination.

**cURL:**

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/" \
  -H "Authorization: Bearer <access_token_from_login>"
```

Filtering by company and paginating manually:

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/?company=3444&page=1&page_size=15" \
  -H "Authorization: Bearer <access_token_from_login>"
```

**Success response `200 OK`:**

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

**Possible error responses:**

- `401` — missing/invalid/expired token
- `403` — authenticated but `is_verified = False`

---

## 4. `GET /v1/affiliate/providers/<id>/`

Retrieves (or updates, via `PUT`) a single provider by its UUID. A user
can only access their own provider record; superusers can access any
record (enforced by `has_permission`).

**cURL — retrieve:**

```bash
curl -X GET "http://127.0.0.1:8000/v1/affiliate/providers/6ab07505-975f-4d45-9293-11f8971fb1c7/" \
  -H "Authorization: Bearer <access_token_from_login>"
```

**Success response `200 OK`:**

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

**cURL — update (`PUT`, full payload required):**

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

**Possible error responses:**

- `404` — `{"error": "Not found"}` when the UUID doesn't exist
- `403` — trying to access/update a provider that isn't yours (and you're
  not a superuser)
- `400` — validation errors on `PUT`

---

## Full example flow (chaining the calls above)

```bash
# 1) Sign up a fake provider
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

# 2) Click the verification link emailed to the fake address
#    (or hit GET /v1/auth/email-verify/<access_token_from_step_1>/ directly)

# 3) Log in to get a usable access/refresh pair
curl -X POST http://127.0.0.1:8000/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "dummy.provider@example.com", "password": "3243434"}'

# 4) List your own provider(s)
curl -X GET http://127.0.0.1:8000/v1/affiliate/providers/ \
  -H "Authorization: Bearer <access_token_from_step_3>"

# 5) Fetch one provider by id
curl -X GET http://127.0.0.1:8000/v1/affiliate/providers/6ab07505-975f-4d45-9293-11f8971fb1c7/ \
  -H "Authorization: Bearer <access_token_from_step_3>"
```
