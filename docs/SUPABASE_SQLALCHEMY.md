# Connecting to Supabase with SQLAlchemy

Supabase exposes a standard Postgres connection string. With Python 3.12 you can rely on `psycopg2-binary` directly; the snippet below follows Supabase’s guidance and uses `python-dotenv` to load credentials from a `.env` file.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os

load_dotenv()

database_url = os.environ["EPR_DATABASE_URL"]

# For Supabase’s transaction/session poolers disable SQLAlchemy’s pooling:
engine = create_engine(database_url, poolclass=NullPool)

try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as exc:  # noqa: BLE001
    print(f"Failed to connect: {exc}")
```

Populate `.env` with the Supabase DSN. For example:

```
EPR_DATABASE_URL=postgresql+psycopg2://postgres:Omen%402025@db.dphneelvofreiuchskcn.supabase.co:5432/postgres?sslmode=require
```

The core service reads this environment variable through `AppSettings` and Alembic uses the same value (escaping `%` automatically).***
