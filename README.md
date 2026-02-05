# Tempo

A lightweight FastAPI platform for building modular API services. Addons are
auto-discovered, configuration is INI-based with env-var and CLI overrides, and
an optional database layer is ready when you need it.
---

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
# Clone and install
git clone <repo-url>
cd tempo
uv sync          # creates .venv and installs everything from uv.lock

# Copy the example config
cp tempo.conf.example tempo.conf
```

That's it. All commands below can be prefixed with `uv run` to use the managed
environment (e.g. `uv run tempo-bin server myapi`), or you can activate the
venv the usual way (`source .venv/bin/activate`) and run `tempo-bin` directly.

---

## Getting started

```bash
# Start the server (development mode with hot reload)
uv run tempo-bin server myapi --reload

# Start on a custom port
uv run tempo-bin server myapi --port 9000

# Start with a specific config file
uv run tempo-bin server myapi --config ./my-tempo.conf
```

The server boots, auto-discovers everything inside `addons/`, and serves the
API. Swagger docs are available at `http://localhost:8000/docs` by default.

---

## CLI commands

| Command | Description |
|---|---|
| `server <name>` | Start the API server |
| `scaffold <name>` | Generate a new addon module from a template |
| `help` | List available commands |

### server

```
./tempo-bin server <name> [options]

Options:
  --config, -c    Path to config file (default: ./tempo.conf)
  --host          Host to bind (default: 0.0.0.0)
  --port          Port to bind (default: 8000)
  --reload        Enable auto-reload (dev mode)
  --no-reload     Disable auto-reload (default)
  --workers       Number of worker processes (default: 1)
```

### scaffold

Generates a full CRUD addon module from a template.

```
./tempo-bin scaffold <name> [dest]

Options:
  -t, --template  Template name or path (default: module)
  dest            Target directory (default: addons)
```

Example — creates `addons/users/` with router, controller, service, schemas,
and models stubs:

```bash
uv run tempo-bin scaffold users
```

---

## Configuration

Copy `tempo.conf.example` to `tempo.conf` in the project root. Settings are
loaded in this priority order (highest first):

1. CLI flags (`--port`, `--host`, …)
2. Environment variables (`TEMPO_SERVER_PORT`, …)
3. `tempo.conf` file
4. Built-in defaults

### Key settings

```ini
[server]
host       = 0.0.0.0
port       = 8000
reload     = false
workers    = 1
```

---

## Addons

Everything inside `addons/` is auto-discovered at startup. The only requirement
is a `router.py` that exposes a FastAPI `APIRouter` named `router`:

```
addons/
└── users/
    ├── __init__.py
    ├── router.py       # must contain: router = APIRouter(...)
    ├── controller.py
    ├── service.py
    ├── schemas.py
    └── models.py
```

Use `scaffold` to generate this structure automatically — it wires up full
CRUD endpoints out of the box with an in-memory data store you can swap for a
real database when ready.

---

## Database

The database layer is optional. It is a no-op unless you configure a
connection URL.

### Setup

Add a `[database]` section to your `tempo.conf`:

```ini
[database]
url = postgresql://user:password@localhost:5432/dbname
```

### Usage

```python
from tempo.db import db

# Guard against unconfigured database
if db.is_configured:

    # Raw SQLAlchemy connection (auto-closes at end of block)
    with db.cr as conn:
        result = conn.execute(text("SELECT * FROM users"))
        rows = result.fetchall()

    # ORM session — ready for SQLModel/SQLAlchemy models
    with db.session as s:
        s.add(user)
        s.commit()
```

Both `db.cr` and `db.session` return a **new** instance on every access —
each request or task gets its own isolated connection/session with no shared
state.
