# AuditHotel - Dashboard de Auditoria Hoteleira

## Visão Geral
Sistema de auditoria hoteleira para recepcionistas que lê PDFs de relatórios hoteleiros (incluindo PDFs escaneados via OCR), categoriza hóspedes automaticamente e detecta divergências de tarifa.

## Problem Statement Original
- Dashboard de auditoria para hotel
- Leitura de PDFs de relatórios hoteleiros
- Categorização automática por origem (Melia, Booking, Expedia = PGTO_DIRETO)
- Detecção de divergências de valor de tarifa
- Separação por categorias (Faturados, Grupos, Confidenciais, etc.)
- Sem armazenamento - cada upload limpa dados anteriores
- Exportação de dados disponível

## User Personas
1. **Recepcionista de Hotel** - Usuário principal que precisa verificar auditoria antes de rodar processo no VHF
2. **Auditor** - Analisa divergências e categorização de hóspedes

## Core Requirements (Estáticos)
- Upload de PDF de relatório hoteleiro
- OCR para PDFs escaneados
- Categorização automática por origem e observações
- Detecção de divergências de tarifa
- Listagem de saídas previstas (hoje + amanhã)
- Exportação CSV dos dados

## Funcionalidades Implementadas (17/03/2026)
- [x] Upload de PDF com processamento OCR (tesseract)
- [x] Extração de dados: UH, Nome, Diária, Chegada, Partida, Observações
- [x] Categorização automática:
  - PGTO_DIRETO: Melia, Booking, Expedia, Travelscape, "pagamento direto"
  - FATURADO: "faturar", "faturado"
  - CONFIDENCIAL: Bancorbras, "confidencial"
  - ONLINE_B2B: "debitar", padrão RES+números
  - GRUPO: GRUF
  - CORTESIA: "cortesia"
- [x] Detecção de divergências (excluindo PGTO_DIRETO e ONLINE_B2B)
- [x] Saídas: partida = hoje OU amanhã
- [x] Dashboard com métricas: Revenue, ADR, contagens por categoria
- [x] Filtros por categoria na página de Registros
- [x] Exportação CSV
- [x] Botão Limpar para resetar dados
- [x] Design moderno dark theme

## Arquitetura
- **Frontend**: React.js + Tailwind CSS
- **Backend**: FastAPI (Python)
- **OCR**: Tesseract OCR + pdf2image + pdfplumber
- **Armazenamento**: Nenhum (stateless)

## APIs
- `POST /api/upload-pdf` - Upload e processamento de PDF
- `GET /api/health` - Health check

## Backlog (Priorizado)
### P0 (Crítico)
- [x] MVP Completo

### P1 (Alta Prioridade)
- [ ] Melhorar precisão do OCR para PDFs de baixa qualidade
- [ ] Suporte a múltiplos formatos de relatório

### P2 (Média Prioridade)
- [ ] Histórico local (localStorage) de auditorias anteriores
- [ ] Comparação entre relatórios de dias diferentes
- [ ] Relatório de resumo para impressão

### P3 (Baixa Prioridade)
- [ ] Modo offline (PWA)
- [ ] Integração com sistemas PMS

## Próximas Tarefas
1. Testar com diferentes PDFs de relatório
2. Ajustar regras de categorização conforme feedback
3. Melhorar extração de valor da observação para divergências
