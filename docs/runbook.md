docker compose up -d
docker compose ps                  # postgres і redis мають бути healthy
cd services\management-api
.\.venv\Scripts\Activate.ps1
alembic current                    # має показати ревізію з позначкою (head)
uvicorn app.main:app --reload --port 8000