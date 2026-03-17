from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pdfplumber
import io
import tempfile

# Tentar importar OCR
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RegistroHospede(BaseModel):
    uh: str
    nome: str
    categoria: str
    pool: str
    diaria: float
    cliente: str
    partida: str
    chegada: str
    reserva: str
    observacao: str
    tipo_classificacao: str
    valor_observacao: Optional[float] = None
    divergencia: Optional[float] = None

class RelatorioProcessado(BaseModel):
    data_relatorio: str
    total_hospedes: int
    total_quartos: int
    revenue_total: float
    adr: float
    registros: List[RegistroHospede]
    faturados: List[RegistroHospede]
    grupos: List[RegistroHospede]
    confidenciais: List[RegistroHospede]
    pgto_direto: List[RegistroHospede]
    online_b2b: List[RegistroHospede]
    cortesias: List[RegistroHospede]
    saidas: List[RegistroHospede]
    divergencias: List[RegistroHospede]

def parse_valor(texto: str) -> float:
    """Converte valor brasileiro (1.234,56) para float"""
    if not texto:
        return 0.0
    texto = str(texto).strip()
    texto = re.sub(r'[^\d,.]', '', texto)
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except:
        return 0.0

def extrair_valor_observacao(obs: str) -> Optional[float]:
    """Extrai valor monetário da observação"""
    if not obs:
        return None
    obs_upper = obs.upper()
    
    patterns = [
        r'TRF\s*([\d.,]+)',
        r'R\$\s*([\d.,]+)',
        r'TOTAL\s*R\$?\s*([\d.,]+)',
        r'(\d{1,3}(?:\.\d{3})*,\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, obs_upper)
        if match:
            valor = parse_valor(match.group(1))
            if valor > 0:
                return valor
    return None

def classificar_registro(nome: str, cliente: str, obs: str) -> str:
    """
    Classifica o registro baseado em origem e observações
    Prioridade: Origem > Observação > Padrões
    """
    nome = (nome or '').upper()
    cliente = (cliente or '').upper()
    obs = (obs or '').upper()
    
    # 0. GRUPO - Verificar GRUF no início (reservas de grupo)
    # GRUF aparece na linha original do PDF
    if 'GRUF' in obs or 'GRUPO' in obs or 'GRUPO' in cliente:
        return 'GRUPO'
    
    # 1. PGTO_DIRETO - Origem (Melia, Booking, Expedia) - PRIORIDADE ALTA
    origens_pgto_direto = ['MELIA.COM', 'MELIA', 'BOOKING.COM', 'BOOKING', 'EXPEDIA', 'TRAVELSCAPE']
    for origem in origens_pgto_direto:
        if origem in cliente or origem in obs:
            return 'PGTO_DIRETO'
    
    # 2. PGTO_DIRETO - Observação (pagamento direto, pgmt direto)
    if any(x in obs for x in ['PAGAMENTO DIRETO', 'PGMT DIRETO', 'PGTO DIRETO', 'PAG DIRETO']):
        return 'PGTO_DIRETO'
    
    # 3. CONFIDENCIAL - Bancorbras ou observação "confidencial"
    if 'BANCORBRAS' in cliente or 'BANCORBRAS' in obs:
        return 'CONFIDENCIAL'
    if 'CONFIDENCIAL' in obs or 'CONFIDENCIAL' in cliente:
        return 'CONFIDENCIAL'
    
    # 4. FATURADO - Menção de faturado/faturar
    if any(x in obs for x in ['FATURADO', 'FATURAR', 'FATURA']):
        return 'FATURADO'
    if 'FATURADO' in cliente:
        return 'FATURADO'
    
    # 5. ONLINE/B2B - Debitar ou padrão res+números
    if 'DEBITAR' in obs:
        return 'ONLINE_B2B'
    if re.search(r'RES\d{6,}', obs.replace(' ', '')):
        return 'ONLINE_B2B'
    
    # 6. CORTESIA - Cortesia ou valor zero
    if 'CORTESIA' in obs or 'CORTESIA' in cliente:
        return 'CORTESIA'
    
    # 7. Default
    return 'OUTROS'

def extrair_texto_ocr(pdf_content: bytes) -> str:
    """Extrai texto do PDF usando OCR"""
    if not OCR_AVAILABLE:
        return ""
    
    try:
        # Converter PDF para imagens
        images = convert_from_bytes(pdf_content, dpi=200)
        
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, lang='por')
            full_text += text + "\n"
        
        return full_text
    except Exception as e:
        logger.error(f"Erro no OCR: {str(e)}")
        return ""

def processar_texto_ocr(texto: str) -> List[RegistroHospede]:
    """Processa o texto extraído por OCR e extrai registros"""
    registros = []
    lines = texto.split('\n')
    
    # Buffer para acumular observações
    current_registro = None
    obs_buffer = []
    
    data_relatorio = None
    
    # Extrair data do relatório (do rodapé)
    for line in lines:
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}', line)
        if date_match:
            data_relatorio = date_match.group(1)
            break
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line or len(line) < 10:
            i += 1
            continue
        
        # Ignorar linhas de cabeçalho/rodapé
        if any(x in line for x in ['FrontOffice', 'Hóspedes cadastrados', 'página', 'Tipo Do Valor', 
                                   'Nome, Sobrenome', 'Alteração nos valores', 'Data Valor', 'HOTEL MELIA']):
            i += 1
            continue
        
        # Detectar linha de hóspede: contém UH (4 dígitos), valores monetários e datas
        uh_match = re.search(r'\b(0\d{3}|1\d{3}|2\d{3})\b', line)  # UH geralmente 0xxx, 1xxx, 2xxx
        valores = re.findall(r'([\d.]+,\d{2})', line)
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', line)
        
        # Linha de hóspede: tem UH, pelo menos 2 valores (0,00 e diária) e 2 datas (chegada/partida)
        if uh_match and len(valores) >= 2 and len(datas) >= 2:
            # Salvar registro anterior
            if current_registro:
                current_registro['observacao'] = ' '.join(obs_buffer).strip()
                registros.append(criar_registro_objeto(current_registro, data_relatorio))
                obs_buffer = []
            
            # Extrair UH
            uh = uh_match.group(1)
            idx_uh = line.find(uh)
            
            # Nome: texto antes do UH (remover códigos)
            nome_part = line[:idx_uh].strip()
            nome_cleaned = re.sub(r'\b(PVEZ|SPEC|GRUF|MERV|MRSI|INVE|MRPL|\d{9}|Sim)\b', '', nome_part)
            nome_cleaned = re.sub(r'\s+N\s+', ' ', nome_cleaned)  # Remove "N" isolado
            nome_cleaned = re.sub(r'\s+', ' ', nome_cleaned).strip()
            nome_cleaned = re.sub(r'^[\*"\s]+|[\*"\s]+$', '', nome_cleaned)
            
            # Verificar se é GRUPO (GRUF na linha)
            is_gruf = 'GRUF' in line
            
            # Valor da diária: segundo valor (primeiro é 0,00 ou valor pensão)
            diaria = parse_valor(valores[1]) if len(valores) >= 2 else 0.0
            
            # Cliente: identificar pela linha
            cliente = ''
            for kw in ['BOOKING.COM', 'BOOKING', 'MELIA.COM', 'MELIA', 'EXPEDIA', 'TRAVELSCAPE', 
                      'BANCORBRAS', 'ADVANTOS', 'EMBAIXADA', 'TRANSPORTES', 'EHTLRESERV']:
                if kw in line.upper():
                    cliente = kw.replace('.COM', '')
                    break
            
            # Reserva
            reserva_match = re.search(r'(\d{9})', line)
            
            # Observação inicial com marcador GRUF se aplicável
            obs_inicial = 'GRUF // ' if is_gruf else ''
            
            current_registro = {
                'uh': uh,
                'nome': nome_cleaned[:50] if nome_cleaned else f'Hóspede {uh}',
                'cliente': cliente,
                'diaria': diaria,
                'chegada': datas[0],
                'partida': datas[1] if len(datas) > 1 else datas[0],
                'reserva': reserva_match.group(1) if reserva_match else '',
                'observacao': obs_inicial,
                'pool': 'Sim' if 'Sim' in line else ''
            }
        
        # Linha somente com data e valor (alteração de diária) - ignorar
        elif re.match(r'^\d{2}/\d{2}/\d{4}\s+[\d.,]+$', line):
            pass
        
        # Linha de observação
        elif current_registro and line:
            # Verificar se é observação válida
            if not re.match(r'^(Data|Valor|[\d.,]+)$', line.strip()):
                obs_buffer.append(line)
        
        i += 1
    
    # Salvar último registro
    if current_registro:
        current_registro['observacao'] = ' '.join(obs_buffer).strip()
        registros.append(criar_registro_objeto(current_registro, data_relatorio))
    
    return registros, data_relatorio

def criar_registro_objeto(reg_dict: dict, data_relatorio: str) -> RegistroHospede:
    """Cria objeto RegistroHospede a partir do dicionário"""
    tipo = classificar_registro(
        reg_dict.get('nome', ''),
        reg_dict.get('cliente', ''),
        reg_dict.get('observacao', '')
    )
    
    valor_obs = extrair_valor_observacao(reg_dict.get('observacao', ''))
    divergencia = None
    
    # Divergência apenas para tipos que não são PGTO_DIRETO ou ONLINE_B2B
    diaria = reg_dict.get('diaria', 0)
    if valor_obs and tipo not in ['PGTO_DIRETO', 'ONLINE_B2B'] and diaria > 0:
        diff = abs(diaria - valor_obs)
        if diff > 1:  # Tolerância de R$ 1
            divergencia = diff
    
    return RegistroHospede(
        uh=reg_dict.get('uh', ''),
        nome=reg_dict.get('nome', ''),
        categoria=tipo,
        pool=reg_dict.get('pool', ''),
        diaria=diaria,
        cliente=reg_dict.get('cliente', ''),
        partida=reg_dict.get('partida', ''),
        chegada=reg_dict.get('chegada', ''),
        reserva=reg_dict.get('reserva', ''),
        observacao=reg_dict.get('observacao', ''),
        tipo_classificacao=tipo,
        valor_observacao=valor_obs,
        divergencia=divergencia
    )

def extrair_registros_avancado(pdf_content: bytes) -> RelatorioProcessado:
    """Extração avançada de registros do PDF usando OCR"""
    registros = []
    data_relatorio = None
    
    # Primeiro tenta pdfplumber (PDF nativo)
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 100:
                    # PDF tem texto nativo, processar
                    break
            else:
                text = None
    except:
        text = None
    
    # Se não tem texto nativo, usa OCR
    if not text or len(text.strip()) < 100:
        logger.info("PDF sem texto nativo, usando OCR...")
        texto_ocr = extrair_texto_ocr(pdf_content)
        if texto_ocr:
            registros, data_relatorio = processar_texto_ocr(texto_ocr)
    else:
        # Processar texto nativo
        registros, data_relatorio = processar_texto_ocr(text)
    
    if not data_relatorio:
        data_relatorio = datetime.now().strftime('%d/%m/%Y')
    
    # Classificar registros
    faturados = [r for r in registros if r.tipo_classificacao == 'FATURADO']
    grupos = [r for r in registros if r.tipo_classificacao == 'GRUPO']
    confidenciais = [r for r in registros if r.tipo_classificacao == 'CONFIDENCIAL']
    pgto_direto = [r for r in registros if r.tipo_classificacao == 'PGTO_DIRETO']
    online_b2b = [r for r in registros if r.tipo_classificacao == 'ONLINE_B2B']
    cortesias = [r for r in registros if r.tipo_classificacao == 'CORTESIA']
    
    # Saídas: partida = data do relatório OU próximo dia
    saidas = []
    if data_relatorio:
        try:
            from datetime import datetime, timedelta
            dt_relatorio = datetime.strptime(data_relatorio, '%d/%m/%Y')
            dt_amanha = dt_relatorio + timedelta(days=1)
            data_amanha = dt_amanha.strftime('%d/%m/%Y')
            saidas = [r for r in registros if r.partida in [data_relatorio, data_amanha]]
        except:
            saidas = [r for r in registros if r.partida == data_relatorio]
    
    # Divergências (excluindo PGTO_DIRETO e ONLINE_B2B)
    divergencias = [r for r in registros if r.divergencia and r.divergencia > 0]
    
    # Calcular totais
    revenue_total = sum(r.diaria for r in registros)
    total_quartos = len(set(r.uh for r in registros if r.uh))
    adr = revenue_total / total_quartos if total_quartos > 0 else 0
    
    return RelatorioProcessado(
        data_relatorio=data_relatorio,
        total_hospedes=len(registros),
        total_quartos=total_quartos,
        revenue_total=revenue_total,
        adr=adr,
        registros=registros,
        faturados=faturados,
        grupos=grupos,
        confidenciais=confidenciais,
        pgto_direto=pgto_direto,
        online_b2b=online_b2b,
        cortesias=cortesias,
        saidas=saidas,
        divergencias=divergencias
    )

@api_router.get("/")
async def root():
    return {"message": "API de Auditoria Hoteleira"}

@api_router.post("/upload-pdf", response_model=RelatorioProcessado)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload e processamento de PDF de relatório hoteleiro"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
    
    content = await file.read()
    resultado = extrair_registros_avancado(content)
    
    return resultado

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "ocr_available": OCR_AVAILABLE}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
