# Spec: Registration (Updated)

## Overview

This step implements user account creation for Spendly.

The existing `GET /register` route renders the registration form. This step extends functionality by adding a `POST /register` handler that:

* Validates user input (name, email, password, confirm password)
* Normalizes the email (case-insensitive handling)
* Hashes the password using Werkzeug
* Inserts a new user into the `users` table
* Redirects to `/login` with a success message on completion

On failure, the form is re-rendered with a clear inline error while preserving user input (except passwords).

A `SECRET_KEY` is also configured to enable session and flash messaging.

---

## Depends on

* Step 1 — Database Setup
  (`database/db.py` must provide `get_db()`, `init_db()`, and a `users` table with a UNIQUE email constraint)

---

## Routes

* `GET /register`
  Render the registration form *(already exists; unchanged)*

* `POST /register`
  Validate input, create user, redirect to login *(new)*

---

## Database Requirements

No schema changes in this step, but the following must already be true:

* `users` table exists with:

  * `id`
  * `name`
  * `email` (**UNIQUE constraint required**)
  * `password_hash`
  * `created_at`

---

## Templates

### Modify: `templates/register.html`

* Add a **Confirm Password** input field:

```html
<input type="password" name="confirm_password" required>
```

* Preserve user input on validation error:

  * Name → `value="{{ name or '' }}"`
  * Email → `value="{{ email or '' }}"`
  * Do **not** preserve password fields

* Existing `{{ error }}` display remains unchanged

---

## Files to change

### `app.py`

#### Imports

Add:

```python
from flask import request, redirect, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash
```

---

#### App Configuration

```python
app.secret_key = "dev-secret-change-me"  # replace with env var in production
```

---

#### Register Route (GET + POST)

### Input Handling

* Extract:

  * `name`
  * `email`
  * `password`
  * `confirm_password`

* Normalize email:

```python
email = request.form.get("email", "").strip().lower()
```

---

### Validation Rules

* All fields must be non-empty
* Password must be at least 8 characters
* Password and confirm password must match

---

### Error Handling

On validation failure:

* Re-render `register.html`
* Pass:

  * `error`
  * `name`
  * `email`

---

### Database Insert

* Use parameterized query:

```sql
INSERT INTO users (name, email, password_hash)
VALUES (?, ?, ?)
```

* Hash password using:

```python
generate_password_hash(password)
```

---

### Duplicate Email Handling

* Catch:

```python
sqlite3.IntegrityError
```

* Return user-friendly error:

> "An account with that email already exists."

---

### Success Flow

* Flash success message:

```python
flash("Registration successful. Please log in.")
```

* Redirect:

```python
return redirect(url_for("login"))
```

* Do **not** create session (handled in Step 03)

---

## Database Connection Handling

Follow the contract defined in `get_db()`:

* If it uses Flask’s `g` (app context), **do not manually close the connection**
* If it returns a fresh connection, ensure proper commit/close handling

---

## Rules for Implementation

* No ORMs (no SQLAlchemy) — use raw `sqlite3`
* Always use parameterized queries (`?`)
* Never store plaintext passwords
* Normalize email before storing
* Enforce one user per email (via UNIQUE constraint)
* All templates must extend `base.html`
* Use existing CSS variables (no hardcoded styles)
* Do not create login session in this step

---

## Definition of Done

* [ ] `GET /register` renders the form correctly
* [ ] Form includes **confirm password field**
* [ ] Submitting valid data:

  * Creates a new user row
  * Stores hashed password (not plaintext)
  * Redirects to `/login`
  * Shows success flash message
* [ ] Missing fields → inline error shown
* [ ] Password < 8 chars → inline error
* [ ] Password mismatch → inline error
* [ ] Duplicate email → inline error
* [ ] Email stored in lowercase (case-insensitive handling)
* [ ] Name and email persist after validation error
* [ ] Password fields are not persisted
* [ ] App runs without errors (`uv run app.py`)

---

## Final Note

This version keeps the implementation clean and scoped for Step 02 while improving UX, data integrity, and alignment with real-world product requirements—without introducing unnecessary complexity.
