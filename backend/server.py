from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import re
import json
import base64
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import pdfplumber
import fitz  # PyMuPDF
import io
from openai import OpenAI

from motor.motor_asyncio import AsyncIOMotorClient

# Load Environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# MongoDB Connection
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'nexus_auditor')
db = None
if MONGO_URL:
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        logger.info(f"✅ MongoDB Neural Link Active: {DB_NAME}")
    except Exception as e:
        logger.error(f"❌ MongoDB initialization failed: {e}")

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NexusBackend")

# Models for Hotel Audit (Legacy support)
class RegistroHospede(BaseModel):
    uh: str
    nome: str
    categoria: str
    pool: str = ""
    diaria: float
    cliente: str = ""
    partida: str = ""
    chegada: str = ""
    reserva: str = ""
    observacao: str = ""
    tipo_classificacao: str = ""
    valor_observacao: Optional[float] = None
    divergencia: Optional[float] = None

class RelatorioProcessado(BaseModel):
    data_relatorio: str
    total_hospedes: int
    total_quartos: int
    revenue_total: float
    adr: float
    registros: List[RegistroHospede]
    faturados: List[RegistroHospede] = []
    grupos: List[RegistroHospede] = []
    confidenciais: List[RegistroHospede] = []
    pgto_direto: List[RegistroHospede] = []
    online_b2b: List[RegistroHospede] = []
    cortesias: List[RegistroHospede] = []
    saidas: List[RegistroHospede] = []
    divergencias: List[RegistroHospede] = []

# Models for Nexus Insumos
class MaterialItem(BaseModel):
    product_name: str
    quantity: float
    unit: str = "un"
    amount: float = 0.0
    category: str = "Outros"

class InsumosAnalysis(BaseModel):
    items: List[MaterialItem]
    summary: dict = {"total": 0.0}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- LEGACY PARSING LOGIC (RESTORED) ---
def parse_valor(texto: str) -> float:
    if not texto: return 0.0
    texto = str(texto).strip()
    texto = re.sub(r'[^\d,.]', '', texto)
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return 0.0

def extrair_valor_observacao(obs: str) -> Optional[float]:
    if not obs: return None
    obs_upper = obs.upper()
    patterns = [r'TRF\s*([\d.,]+)', r'R\$\s*([\d.,]+)', r'TOTAL\s*R\$?\s*([\d.,]+)', r'(\d{1,3}(?:\.\d{3})*,\d{2})']
    for pattern in patterns:
        match = re.search(pattern, obs_upper)
        if match:
            valor = parse_valor(match.group(1))
            if valor > 0: return valor
    return None

def classificar_registro(nome: str, cliente: str, obs: str) -> str:
    nome = (nome or '').upper()
    cliente = (cliente or '').upper()
    obs = (obs or '').upper()
    if 'GRUF' in obs or 'GRUPO' in obs or 'GRUPO' in cliente: return 'GRUPO'
    origens_pgto_direto = ['MELIA.COM', 'MELIA', 'BOOKING.COM', 'BOOKING', 'EXPEDIA', 'TRAVELSCAPE']
    for origem in origens_pgto_direto:
        if origem in cliente or origem in obs: return 'PGTO_DIRETO'
    if any(x in obs for x in ['PAGAMENTO DIRETO', 'PGMT DIRETO', 'PGTO DIRETO', 'PAG DIRETO']): return 'PGTO_DIRETO'
    if 'BANCORBRAS' in cliente or 'BANCORBRAS' in obs or 'CONFIDENCIAL' in obs: return 'CONFIDENCIAL'
    if any(x in obs for x in ['FATURADO', 'FATURAR', 'FATURA']) or 'FATURADO' in cliente: return 'FATURADO'
    if 'DEBITAR' in obs or re.search(r'RES\d{6,}', obs.replace(' ', '')): return 'ONLINE_B2B'
    if 'CORTESIA' in obs or 'CORTESIA' in cliente: return 'CORTESIA'
    return 'OUTROS'

def processar_texto_basico(texto: str) -> List[RegistroHospede]:
    registros = []
    lines = texto.split('\n')
    current_registro = None
    obs_buffer = []
    data_relatorio = None
    
    for line in lines:
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}', line)
        if date_match:
            data_relatorio = date_match.group(1)
            break

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10: continue
        if any(x in line for x in ['FrontOffice', 'Hóspedes cadastrados', 'página', 'Tipo Do Valor']): continue
        
        uh_match = re.search(r'\b(0\d{3}|1\d{3}|2\d{3})\b', line)
        valores = re.findall(r'([\d.]+,\d{2})', line)
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', line)
        
        if uh_match and len(valores) >= 2 and len(datas) >= 2:
            if current_registro:
                current_registro['observacao'] = ' '.join(obs_buffer).strip()
                registros.append(criar_registro_objeto(current_registro, data_relatorio))
                obs_buffer = []
            
            uh = uh_match.group(1)
            idx_uh = line.find(uh)
            nome_part = line[:idx_uh].strip()
            nome_cleaned = re.sub(r'\b(PVEZ|SPEC|GRUF|MERV|MRSI|INVE|MRPL|\d{9}|Sim)\b', '', nome_part)
            nome_cleaned = re.sub(r'\s+', ' ', nome_cleaned).strip()
            
            current_registro = {
                'uh': uh,
                'nome': nome_cleaned[:50] if nome_cleaned else f'Hóspede {uh}',
                'diaria': parse_valor(valores[1]) if len(valores) >= 2 else 0.0,
                'chegada': datas[0],
                'partida': datas[1] if len(datas) > 1 else datas[0],
                'pool': 'Sim' if 'Sim' in line else '',
                'observacao': 'GRUF // ' if 'GRUF' in line else ''
            }
        elif current_registro and line:
            if not re.match(r'^(Data|Valor|[\d.,]+)$', line.strip()):
                obs_buffer.append(line)
    
    if current_registro:
        current_registro['observacao'] = ' '.join(obs_buffer).strip()
        registros.append(criar_registro_objeto(current_registro, data_relatorio))
    
    return registros, data_relatorio

def criar_registro_objeto(reg_dict: dict, data_relatorio: str) -> RegistroHospede:
    tipo = classificar_registro(reg_dict.get('nome', ''), reg_dict.get('cliente', ''), reg_dict.get('observacao', ''))
    valor_obs = extrair_valor_observacao(reg_dict.get('observacao', ''))
    divergencia = None
    diaria = reg_dict.get('diaria', 0)
    if valor_obs and tipo not in ['PGTO_DIRETO', 'ONLINE_B2B'] and diaria > 0:
        diff = abs(diaria - valor_obs)
        if diff > 1: divergencia = diff
    
    return RegistroHospede(
        uh=reg_dict.get('uh', ''), nome=reg_dict.get('nome', ''), categoria=tipo,
        pool=reg_dict.get('pool', ''), diaria=diaria, cliente=reg_dict.get('cliente', ''),
        partida=reg_dict.get('partida', ''), chegada=reg_dict.get('chegada', ''),
        reserva=reg_dict.get('reserva', ''), observacao=reg_dict.get('observacao', ''),
        tipo_classificacao=tipo, valor_observacao=valor_obs, divergencia=divergencia
    )

# --- GPT-4O VISION PARSER ---
async def analyze_with_vision(image_bytes: bytes, filename: str, is_hotel: bool = True) -> dict:
    if not openai_client: return None
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        prompt = "Extraia dados do relatório hoteleiro" if is_hotel else "Extraia itens e quantidades da lista de materiais"
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é o Especialista Nexus AI. Retorne APENAS JSON."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return None

# --- ROUTES ---
@api_router.get("/")
async def root():
    return {"message": "Nexus Auditor AI Core Active"}

@api_router.post("/upload-pdf", response_model=RelatorioProcessado)
async def upload_pdf(file: UploadFile = File(...)):
    content = await file.read()
    
    # Tenta extrair texto nativo primeiro
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text: text += page_text + "\n"
    except: pass
    
    if len(text) < 100:
        # Tenta Vision se texto nativo falhar
        doc = fitz.open(stream=content, filetype="pdf")
        page = doc.load_page(0)
        img_bytes = page.get_pixmap().tobytes("jpeg")
        doc.close()
        vision_data = await analyze_with_vision(img_bytes, file.filename)
    
    registros, data_relatorio = processar_texto_basico(text)
    
    # Post-process statistics
    revenue = sum(r.diaria for r in registros)
    total_quartos = len(set(r.uh for r in registros if r.uh))
    
    result = RelatorioProcessado(
        data_relatorio=data_relatorio or datetime.now().strftime('%d/%m/%Y'),
        total_hospedes=len(registros),
        total_quartos=total_quartos,
        revenue_total=revenue,
        adr=revenue/total_quartos if total_quartos > 0 else 0,
        registros=registros,
        faturados=[r for r in registros if r.tipo_classificacao == 'FATURADO'],
        grupos=[r for r in registros if r.tipo_classificacao == 'GRUPO'],
        confidenciais=[r for r in registros if r.tipo_classificacao == 'CONFIDENCIAL'],
        pgto_direto=[r for r in registros if r.tipo_classificacao == 'PGTO_DIRETO'],
        online_b2b=[r for r in registros if r.tipo_classificacao == 'ONLINE_B2B'],
        cortesias=[r for r in registros if r.tipo_classificacao == 'CORTESIA'],
        saidas=[r for r in registros if r.partida == (data_relatorio or datetime.now().strftime('%d/%m/%Y'))],
        divergencias=[r for r in registros if r.divergencia]
    )

    # Persistence to MongoDB
    if db is not None:
        try:
            report_doc = result.model_dump()
            report_doc['timestamp'] = datetime.now(timezone.utc)
            report_doc['filename'] = file.filename
            await db.reports.insert_one(report_doc)
            logger.info(f"💾 Relatório persistido no MongoDB")
        except Exception as e:
            logger.error(f"❌ Error saving to MongoDB: {e}")

    return result

@api_router.post("/analyze-insumos")
async def analyze_insumos(file: UploadFile = File(...)):
    content = await file.read()
    vision_result = await analyze_with_vision(content, file.filename, is_hotel=False)
    
    if db is not None and vision_result:
        try:
            items = vision_result.get('items', vision_result.get('transactions', []))
            if items:
                await db.insumos.insert_many([{**item, 'timestamp': datetime.now(timezone.utc)} for item in items])
                logger.info("💾 Itens de insumos persistidos.")
        except Exception as e:
            logger.error(f"❌ Error saving insumos to MongoDB: {e}")

    return vision_result or {"items": []}

app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
