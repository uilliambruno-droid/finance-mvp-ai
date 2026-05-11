# Pluto Finance AI

Assistente financeiro conversacional com foco em Brasil para planejamento financeiro, análise de gastos e orientação educativa de investimentos.

## Principais funcionalidades

- Formulário inicial obrigatório com perfil financeiro
- Memória persistente de perfil, mensagens e transações em `data/runtime/user_state.json`
- Registro automático de gastos e ganhos via chat (ex.: `gastei 150 no ifood`, `recebi 5000 de salário`)
- Meta patrimonial com cálculo de progresso e valor faltante
- Dashboard resumido com renda, patrimônio, meta, progresso, interações e transações
- Respostas-base por cenário financeiro:
  - reserva de emergência
  - dívidas vs investir
  - aportes mensais
  - aposentadoria
  - ETF vs renda fixa
- Feedback estruturado por resposta:
  - voto positivo/negativo
  - nota de 1 a 5
  - comentário livre
  - eventos salvos em `data/runtime/events.jsonl`
- LLM primário via Groq + fallback local via Ollama

## Stack

- Python 3.11+
- Streamlit
- Pandas
- Requests
- python-dotenv
- Groq API (`llama-3.1-8b-instant` por padrão)
- Ollama fallback (`llama3.2:3b-instruct` por padrão)

## Estrutura

- `src/app.py`: aplicação Streamlit principal
- `src/finance_knowledge.py`: regras de conhecimento financeiro e extrações
- `tests/`: testes unitários e de integração
- `docs/`: documentação de arquitetura, prompts, métricas e pitch
- `data/runtime/`: estado persistente e eventos

## Configuração local

```bash
cd /Users/uilliamsantos/Documents/mvp-finance-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crie/ajuste `.env`:

```bash
GROQ_API_KEY=seu_token
GROQ_MODEL=llama-3.1-8b-instant
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b-instruct
```

## Rodar aplicação

```bash
cd /Users/uilliamsantos/Documents/mvp-finance-ai
source venv/bin/activate
streamlit run src/app.py
```

## Testes

```bash
cd /Users/uilliamsantos/Documents/mvp-finance-ai
source venv/bin/activate
python -m py_compile src/app.py src/finance_knowledge.py
python -m pytest -q tests/
```

## Fluxo recomendado de uso

1. Preencha perfil (nome, renda, estilo, objetivo, patrimônio atual e meta)
2. Faça perguntas consultivas no chat
3. Registre gastos/ganhos por linguagem natural
4. Avalie respostas com feedback estruturado
5. Acompanhe progresso de patrimônio no dashboard

## Segurança e limites

- Conteúdo educacional, não recomendação profissional individual
- Não executa operações financeiras reais
- Não solicita senha/código sensível
- Em ativos voláteis (ETF/ações/cripto), inclui alerta de risco
- Escopo fiscal e regulatório prioritário para Brasil

## Deploy

O projeto já contém `render.yaml` para deploy no Render.

Checklist pré-produção:

- `python -m pytest -q tests/` verde
- variáveis `.env` configuradas no ambiente
- conferência do fallback Ollama (opcional)
- revisão final de UX no fluxo completo (formulário -> chat -> feedback)

## Próximos passos sugeridos

- Dashboard de eventos (`events.jsonl`) com métricas em tempo real
- Alertas automáticos de anomalia de gastos por categoria
- Exportação de resumo de plano financeiro em PDF
- Cobertura de testes para fluxo visual de feedback e dashboard
