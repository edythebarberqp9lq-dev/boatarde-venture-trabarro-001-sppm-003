from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Admin/tracking routes
from admin_routes import admin_router, set_db, seed_admin
set_db(db)

# Public registration routes (event sign-up form)
from inscricao_routes import insc_router


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Painel Administrativo API"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# ===== Proxies para evitar CORS/CSP no frontend estático =====
import httpx
from fastapi import HTTPException

@api_router.get("/cep/{cep}")
async def lookup_cep(cep: str):
    cep_clean = ''.join(c for c in cep if c.isdigit())
    if len(cep_clean) != 8:
        raise HTTPException(status_code=400, detail="CEP inválido")
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(f"https://viacep.com.br/ws/{cep_clean}/json/")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="ViaCEP indisponível")
        data = r.json()
        if data.get('erro'):
            raise HTTPException(status_code=404, detail="CEP não encontrado")
        return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar ViaCEP: {e}")


@api_router.get("/ibge/municipios/{uf}")
async def lookup_municipios(uf: str):
    uf = uf.strip().upper()
    if len(uf) != 2:
        raise HTTPException(status_code=400, detail="UF inválida")
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="IBGE indisponível")
        return r.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar IBGE: {e}")


app.include_router(api_router)
app.include_router(admin_router)
app.include_router(insc_router)


@app.on_event("startup")
async def on_startup():
    await seed_admin()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
