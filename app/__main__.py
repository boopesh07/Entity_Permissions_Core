from app.main import app  # pragma: no cover

# Allows `python -m app` to run uvicorn programmatically if desired.
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
