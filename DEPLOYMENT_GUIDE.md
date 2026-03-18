# 🚀 Guia de Implantação Nexus Auditor AI - Hostinger VPS

Este projeto foi configurado para rodar em um servidor **VPS Hostinger** (Ubuntu/Debian) usando **PM2** para processos e **Nginx** como Proxy Reverso.

## 1. Requisitos do Servidor
- Node.js & npm (para o Frontend)
- Python 3.10+ (para o Backend)
- PM2 (`npm install -g pm2`)
- Nginx (`sudo apt install nginx`)
- MongoDB (Pode ser local ou Atlas)

---

## 2. Preparação dos Arquivos
No seu servidor Hostinger, clone o repositório e configure as permissões:
```bash
git clone https://github.com/SeuUsuario/repo.git nexus
cd nexus
```

### Configurando o Backend (Python)
1. Entre na pasta `backend`: `cd backend`
2. Crie um ambiente virtual: `python3 -m venv venv`
3. Ative o venv: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`
5. Crie um arquivo `.env` com:
   - `OPENAI_API_KEY=sua_chave`
   - `MONGO_URL=sua_url_mongodb`
   - `DB_NAME=nexus_auditor`

### Configurando o Frontend (React)
1. Entre na pasta `frontend`: `cd ../frontend`
2. Instale: `npm install`
3. Crie o build: `npm run build`

---

## 3. Inicialização com PM2
O arquivo `ecosystem.config.js` já está pronto na raiz do projeto.
Para iniciar frontend e backend de uma vez:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## 4. Configuração do Nginx (Proxy Reverso)
1. Copie o template: `sudo cp ../nginx.conf /etc/nginx/sites-available/nexus`
2. Ative o site: `sudo ln -s /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/`
3. Reinicie: `sudo systemctl restart nginx`

---

## ✨ Configurações Nexus AI
- **Processamento Neural**: GPT-4o Vision processando PDFs e Fotos.
- **Banco de Dados**: MongoDB salvando todo o histórico de auditoria.
- **Dark Mode**: Estética Fintech ativada por padrão.

---
**Nexus AI** - *The future of financial auditing.*

---

## ✨ Novas Funcionalidades Ativadas:
- **Neural Vision**: Extração de itens de insumos de fotos/rascunhos.
- **Auditoria Hoteleira**: Fallback inteligente para PDFs legados.
- **Persistence**: Todos os relatórios agora são salvos no seu MongoDB.
- **Premium UI**: Dark mode com Glassmorphism e animações neurais.

---
**Nexus AI** - *The future of financial auditing.*
