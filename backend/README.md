# Backend

FastAPI backend scaffold.

## Run locally

Run setup once:

```bash
./setup.sh
```

Then start the API:

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```
