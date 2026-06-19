# Lavrari — Sistema de Gestão de RDOs

Backend do sistema **Lavrari**, desenvolvido para o Hackathon SUAPE/DINFRA 2026. Digitaliza e automatiza o fluxo de Registros Diários de Obra (RDO) com IA generativa embarcada, georreferenciamento de evidências fotográficas e versionamento imutável de documentos.

**API em produção:** `https://lavrari-api.2b9zc5fehjax.br-sao.codeengine.appdomain.cloud`
**Documentação interativa:** `/docs` · `/redoc`

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| API | FastAPI 0.13+ · Python 3.11 · Uvicorn |
| Banco de dados | MongoDB Atlas (Motor async) |
| IA | Groq — Llama 3.3 70B (texto), Llama 4 Scout 17B (visão), gpt-oss-120B (agente ReAct), Whisper large-v3 (áudio) |
| Orquestração IA | LangChain + LangGraph |
| PDF | WeasyPrint (HTML→PDF) · pypdf (merge) |
| Storage | IBM Cloud Object Storage (boto3/S3) |
| Mapas | Cesium Ion (frontend) · Nominatim/OSM (geocodificação reversa) |
| Autenticação | JWT (python-jose) · bcrypt |
| Imagens | Pillow |
| Deploy | IBM Code Engine (br-sao) · IBM Container Registry |

---

## Funcionalidades

### RDO — Registro Diário de Obra
- Criação e edição de RDOs com clima, pessoal direto/indireto, equipamentos, serviços e eventos de restrição
- Clima automático por geolocalização da obra (integração com API de meteorologia)
- Máquina de estados: `rascunho → revisao_externa → revisao_suape → bloqueado → finalizado` com reabertura
- Assinatura digital por perfil (fiscal externo, fiscal SUAPE, admin)
- PDF do RDO com cabeçalho completo (logos, ARTs, responsáveis técnicos) gerado via WeasyPrint

### Versionamento Imutável
- Cada transição de estado gera um snapshot completo (RDO + cabeçalho da obra no momento)
- Ações oficiais (envio, aprovação/reprovação, reabertura, finalização) congelam um **PDF imutável no COS**
- Histórico reproduzível: `GET /rdos/{id}/versoes/{n}/pdf` regenera o documento de qualquer versão
- Alterar responsáveis/ART/logos na obra **não sobrescreve** documentos já emitidos

### Evidências Georreferenciadas
- Upload de fotos com lat/lon obrigatórios, georreferenciadas no mapa 3D (Cesium Ion)
- Análise automática por IA de visão (Llama 4 Scout): descreve atividade em execução, equipamentos e condições de segurança
- Geocodificação reversa automática via Nominatim/OSM
- Endpoint de mapa: `GET /obras/{id}/mapa-evidencias` — todos os pontos de evidência de uma obra para plotagem na linha do tempo

### IA Embarcada
| Recurso | Endpoint | Modelo |
|---------|----------|--------|
| Estruturar RDO por texto | `POST /ia/estruturar-rdo` | Llama 3.3 70B |
| Estruturar RDO por áudio | `POST /ia/estruturar-rdo/audio` | Whisper + Llama 3.3 70B |
| Sugestão de texto (ocorrências/resumo) | `POST /ia/sugestao-texto` | Llama 3.3 70B |
| Análise de imagem | (background no upload de mídia) | Llama 4 Scout 17B |
| Transcrição de áudio avulsa | `POST /ia/transcricao` | Whisper large-v3 |
| Saúde contratual da obra | `GET /ia/saude-obra/{id}` | Llama 3.3 70B |
| Padrões de não conformidade | `GET /ia/padroes-nc/{id}` | Llama 3.3 70B |
| Agente conversacional (chat) | `POST /ia/chat` | gpt-oss-120B (ReAct) |

O `estruturar-rdo` é **idempotente** (não grava nada) — preenche um formulário de RDO a partir de texto livre ou áudio, retornando os campos preenchidos com índice de confiança.

### Gestão de Obras
- Criação de obras com geocodificação automática do endereço pelas coordenadas
- Upload de logos (SUAPE, contratada, fiscalização externa) com redimensionamento automático para caixa 600×200 px
- ART do fiscal SUAPE, ART do fiscal externo e responsáveis técnicos (múltiplos, com ART/CREA)
- Dashboard por obra: total de RDOs, distribuição por status, % de prazo decorrido
- Dossiê executivo (PDF consolidado de todos os RDOs aprovados)
- Evolução visual (linha do tempo fotográfica)

### Permissões Granulares por Obra
- Perfis: `administrador | fiscal_suape | fiscal_externo | fornecedor | consulta`
- Permissões extras temporárias com `expira_em`: `pode_adicionar_info`, `pode_comentar`, `pode_enviar_suape`
- `GET /usuarios/{id}/vinculos` — visão de governança: quem tem qual perfil/permissão em qual obra e até quando

---

## Estrutura do Projeto

```
app/
├── api/v1/
│   ├── deps.py                  # Dependências FastAPI (auth, acesso obra, perfil)
│   └── endpoints/               # Routers: auth, obras, rdos, midias, ia, usuarios, ...
├── core/
│   ├── config/settings.py       # Pydantic Settings (variáveis de ambiente)
│   ├── exceptions.py            # Exceções de domínio → HTTP
│   ├── infrastructure/mongodb/  # MongoManager (Motor, lazy-init, TLS)
│   └── security.py              # JWT + bcrypt
├── globals/
│   ├── enums/                   # Enums: StatusRDO, AcaoVersao, PerfilUsuario, ...
│   └── models/                  # Pydantic models: Obra, RDO, Midia, Empresa, ...
├── repositories/                # Camada de acesso ao MongoDB (CRUD genérico + queries)
└── services/
    ├── ia/
    │   ├── agente.py            # Agente ReAct (LangGraph create_agent)
    │   ├── analytics.py         # Saúde contratual, padrões NC, estruturar-rdo
    │   ├── insights.py          # EstruturarRDOService (texto → campos do RDO)
    │   ├── llm.py               # Fábricas ChatGroq + schemas de saída estruturada
    │   ├── media.py             # Análise de imagem (visão)
    │   ├── service.py           # Facade IAService
    │   └── tools/               # Tools do agente: obras, rdos, saúde, alertas
    ├── geocoding_service.py     # Nominatim OSM (best-effort, timeout 8s)
    ├── image_utils.py           # Pillow: redimensionar_para_caixa (sem distorção)
    ├── obra_service.py          # Obras + vínculos + logos + mapa de evidências
    ├── pdf_service.py           # WeasyPrint: RDO PDF + dossiê + snapshot de versão
    ├── rdo_service.py           # CRUD RDO + clima automático
    ├── storage_service.py       # IBM COS (boto3): fotos, logos, PDFs, dossiês
    ├── versioning_service.py    # Snapshots imutáveis + PDF congelado no COS
    └── workflow_service.py      # Máquina de estados do RDO
```

---

## Configuração Local

### Pré-requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- MongoDB Atlas (ou local com TLS)
- Conta Groq (API key gratuita em console.groq.com)
- IBM Cloud Object Storage (opcional para storage de arquivos)

### Instalação

```bash
git clone <repo>
cd lavrari
uv sync
```

### Variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
DEBUG=false

# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/?appName=app
MONGODB_DATABASE_NAME=lavrari

# JWT
JWT_SECRET_KEY=<string-aleatória-longa>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Groq
GROQ_API_KEY=gsk_...

# Clima (OpenWeatherMap)
WEATHER_API_KEY=...

# IBM Cloud Object Storage
IBM_COS_ENDPOINT=https://s3.br-sao.cloud-object-storage.appdomain.cloud
IBM_COS_ACCESS_KEY=...
IBM_COS_SECRET_KEY=...
IBM_COS_BUCKET_NAME=lavrari
IBM_COS_INSTANCE_CRN=crn:v1:...

# Cesium Ion (frontend)
CESIUM_ION_ACCESS_TOKEN=...
```

### Execução

```bash
# Rodar localmente
uv run uvicorn app.main:app --reload --port 8000

# Criar primeiro admin (setup único)
curl -X POST http://localhost:8000/lavrari/api/v1/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"nome":"Admin","email":"admin@suape.gov.br","senha":"senha123"}'
```

Acesse `http://localhost:8000/docs` para a documentação interativa.

---

## Deploy (IBM Code Engine)

```bash
# Build da imagem
podman build -t br.icr.io/lavrari/lavrari-api:latest .

# Login no registry via token IAM
TOKEN=$(ibmcloud iam oauth-tokens --output json | python3 -c \
  "import sys,json;print(json.load(sys.stdin)['iam_token'].split(' ')[1])")
echo "$TOKEN" | podman login -u iambearer --password-stdin br.icr.io

# Push
podman push br.icr.io/lavrari/lavrari-api:latest

# Atualizar app no Code Engine
ibmcloud target -r br-sao -g Default
ibmcloud ce project select -n lavrari
ibmcloud ce app update --name lavrari-api --image br.icr.io/lavrari/lavrari-api:latest
```

---

## Rotas da API

### Auth
| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/auth/setup` | Cria o primeiro administrador (one-shot) |
| `POST` | `/auth/login` | Login → access + refresh token |
| `POST` | `/auth/refresh` | Renova o access token |
| `POST` | `/auth/logout` | Invalida o refresh token |
| `GET` | `/auth/me` | Dados do usuário autenticado |

### Obras
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/obras/` | Lista obras acessíveis ao usuário |
| `POST` | `/obras/` | Cria obra (admin) |
| `GET/PATCH` | `/obras/{id}` | Detalhe e atualização |
| `POST` | `/obras/{id}/logos/{slot}` | Upload de logo (suape/contratada/fiscalizacao_externa) |
| `GET` | `/obras/{id}/mapa-evidencias` | Pontos georreferenciados para mapa 3D |
| `GET` | `/obras/{id}/dashboard` | Indicadores de progresso |
| `POST` | `/obras/{id}/dossie` | Gera dossiê PDF consolidado |
| `GET/POST/PATCH/DELETE` | `/obras/{id}/usuarios` | Gestão de vínculos e perfis |
| `PATCH` | `/obras/{id}/usuarios/{id}/permissoes` | Permissões temporárias |

### RDOs
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET/POST` | `/rdos/` | Listar e criar RDOs |
| `GET/PATCH/DELETE` | `/rdos/{id}` | Detalhe, edição (rascunho) e exclusão |
| `POST` | `/rdos/{id}/submeter` | Envia para revisão externa ou SUAPE |
| `POST` | `/rdos/{id}/aprovar-externo` | Fiscal externo aprova |
| `POST` | `/rdos/{id}/reprovar-externo` | Fiscal externo reprova com motivo |
| `POST` | `/rdos/{id}/aprovar-suape` | Fiscal SUAPE aprova → bloqueado |
| `POST` | `/rdos/{id}/reprovar-suape` | Fiscal SUAPE reprova com motivo |
| `POST` | `/rdos/{id}/reabrir` | Reabre com justificativa |
| `POST` | `/rdos/{id}/finalizar` | Admin finaliza |
| `GET` | `/rdos/{id}/pdf` | Gera PDF do RDO atual |
| `GET` | `/rdos/{id}/versoes` | Lista versões imutáveis |
| `GET` | `/rdos/{id}/versoes/{n}/pdf` | Reproduz PDF congelado de uma versão |
| `GET/POST` | `/rdos/{id}/midias/` | Evidências fotográficas georreferenciadas |
| `GET/POST` | `/rdos/{id}/comentarios/` | Comentários e solicitações de correção |
| `POST/GET` | `/rdos/{id}/assinar` | Assinatura digital |

### IA
| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/ia/chat` | Agente conversacional com tool calling |
| `POST` | `/ia/estruturar-rdo` | Texto livre → campos do RDO (idempotente) |
| `POST` | `/ia/estruturar-rdo/audio` | Áudio → transcrição → campos do RDO |
| `POST` | `/ia/transcricao` | Transcrição de áudio avulsa |
| `POST` | `/ia/sugestao-texto` | Sugestão de ocorrências/resumo por histórico |
| `GET` | `/ia/saude-obra/{id}` | Índice de saúde contratual com análise IA |
| `GET` | `/ia/padroes-nc/{id}` | Detecta padrões de não conformidade |

---

## Fluxo do RDO

```
            Fornecedor/Admin
                  │
                  ▼
            [RASCUNHO] ◄──────────────────────────────┐
                  │ submeter                           │
                  ▼                                   │ reprovar
        [REVISAO_EXTERNA] ──reprovar──► [RASCUNHO]   │
                  │ aprovar (fiscal externo)           │
                  ▼                                   │
         [REVISAO_SUAPE] ───reprovar──────────────────┘
                  │ aprovar (fiscal SUAPE)
                  ▼
           [BLOQUEADO] ◄──── reabrir ────┐
                  │ finalizar            │
                  ▼                      │
           [FINALIZADO] ─────────────────┘
```

Se a obra não tiver fiscal externo, o RDO vai direto de `rascunho → revisao_suape`.

---

## Modelos Principais

### Obra
- Contrato, objeto, tipologia, local, coordenadas (geocodificadas automaticamente)
- Responsáveis técnicos (lista, com ART/CREA individuais — múltiplos, rastreados por versão)
- ART do fiscal SUAPE e ART do fiscal externo
- Três slots de logo (SUAPE, contratada, fiscalização externa)
- Prazo contratual, datas de vigência e execução

### RDO
- Clima (manhã/tarde) com fonte: `manual | api_clima | transcricao`
- Pessoal direto e indireto (função + quantidade)
- Equipamentos (nome + quantidade)
- Serviços (descrição, situação, grupo)
- Eventos de restrição (8 flags + descrição)
- Ocorrências e resumo do dia (texto livre/IA)

### Versão (rdo_versoes)
- Snapshot completo do RDO + cabeçalho da obra no momento da ação
- `pdf_url` + `pdf_hash` quando a ação gera documento oficial
- Ações que geram PDF: `envio_revisao`, `aprovacao_externa`, `reprovacao_externa`, `aprovacao_suape`, `reprovacao_suape`, `reabertura`, `finalizacao`

---

## Autores

Desenvolvido por **Ivisson Alves** para o Hackathon SUAPE/DINFRA 2026.
