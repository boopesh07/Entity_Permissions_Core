# Connecting to Supabase with SQLAlchemy

Supabase recommends the following pattern when connecting via SQLAlchemy. The example below assumes environment variables containing your database credentials and enables TLS (`sslmode=require`).

```python
from sqlalchemy import create_engine
# from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
# If using Transaction Pooler or Session Pooler, disable SQLAlchemy client side pooling:
# engine = create_engine(DATABASE_URL, poolclass=NullPool)

# Test the connection
try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")
```

For the Omen Entity & Permissions Core service, set `EPR_DATABASE_URL` directly (see `.env.example`). A fully expanded example with URL-encoded password is:

```
EPR_DATABASE_URL=postgresql+psycopg2://postgres:Omen%402025@db.dphneelvofreiuchskcn.supabase.co:5432/postgres?sslmode=require
```
