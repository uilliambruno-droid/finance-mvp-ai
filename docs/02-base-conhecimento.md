# Base de Conhecimento

## Dados Utilizados

Para o Pluto, usamos uma base híbrida com:

1. **Dados estruturados do projeto** (CSV/JSON em `data/`) para personalização e grounding.
2. **Datasets públicos curados do Hugging Face** (em `data/hf/`) para ampliar cobertura global em linguagem de mercado, Q&A e sentimento.

| Arquivo | Formato | Utilização no Agente |
|---------|---------|---------------------|
| `historico_atendimento.csv` | CSV | Contextualizar interações anteriores e manter continuidade de conversa |
| `perfil_investidor.json` | JSON | Personalizar recomendações por perfil, metas e tolerância a risco |
| `produtos_financeiros.json` | JSON | Grounding de recomendações para renda fixa, ETFs, ações e cripto (apenas itens catalogados) |
| `transacoes.csv` | CSV | Analisar padrão de gastos, anomalias e progresso de metas |
| `data/hf/atrost__financial_phrasebank/*.parquet` | Parquet | Trechos para classificação de sentimento financeiro textual |
| `data/hf/virattt__financial-qa-10K/train.parquet` | Parquet | Base de perguntas e respostas financeiras para robustecer respostas educativas |
| `data/hf/OpenFinAL__Financial_Question_Answering/train.parquet` | Parquet | Conversas/FAQ para melhorar estilo de atendimento do assistente |
| `data/hf/zeroshot__twitter-financial-news-sentiment/*.parquet` | Parquet | Contexto de sentimento de notícias financeiras em escala global |
| `data/hf/paperswithbacktest__Stocks-Daily-Price/train.parquet` | Parquet | Série histórica de preços (mercado global, incluindo ativos dos EUA) |
| `data/knowledge/tax_knowledge.json` | JSON | Regras estruturadas educativas de Selic, Tesouro Direto, taxação (BR/internacional), ações, ETFs e cripto |

> [!TIP]
> **Quer um dataset mais robusto?** Você pode utilizar datasets públicos do [Hugging Face](https://huggingface.co/datasets) relacionados a finanças, desde que sejam adequados ao contexto do desafio.

---

## Adaptações nos Dados

> Você modificou ou expandiu os dados mockados? Descreva aqui.

Sim. A base foi expandida em duas camadas:

### 1) Expansão por cobertura global
- Mantivemos os mockados iniciais para personalização do cliente.
- Adicionamos datasets públicos de finanças para ampliar repertório além do contexto local.
- Direcionamos o escopo para uso global, incluindo possibilidade de contexto da bolsa americana.

### 2) Expansão por tipo de tarefa
- **Personal Finance**: transações + perfil + metas.
- **Educação Financeira / QA**: datasets de perguntas e respostas.
- **Sentimento de mercado**: datasets de sentimento em notícias/texto financeiro.
- **Mercado (time series)**: preços históricos para contexto de ativos e comportamento de mercado.
- **Taxação e regras de produto**: base estruturada para responder com consistência sobre IR regressivo, IOF, Selic, Tesouro, ETFs, ações e cripto.
- **Catálogo de ativos**: títulos de renda fixa, ETFs globais, ações e cripto com nível de risco e alerta por ativo.

### 3) Padronização de armazenamento
- Persistimos os datasets baixados em `Parquet` dentro de `data/hf/`.
- Mantemos resumo de auditoria dos datasets em `data/hf/_summary_curated.json`.
- Total atual carregado no projeto: **8 arquivos parquet** (~10MB no snapshot atual).

---

## Estratégia de Integração

### Como os dados são carregados?
> Descreva como seu agente acessa a base de conhecimento.

- **Camada local (core do cliente):** `CSV/JSON` em `data/` são carregados no início da sessão (perfil, transações, produtos, histórico).
- **Camada HF (conhecimento ampliado):** `Parquet` em `data/hf/` são carregados sob demanda por tarefa (QA, sentimento, mercado).
- **Fallback seguro:** se uma fonte não estiver disponível, o Pluto responde com base no catálogo interno e declara limitação.
- **Regras de risco por ativo:** o campo `alerta_risco` em `produtos_financeiros.json` é sempre aplicado na resposta quando o tema for ETF, ação ou cripto.

### Como os dados são usados no prompt?
> Os dados vão no system prompt? São consultados dinamicamente?

Os dados são usados em dois níveis:

1. **System Prompt (regras fixas):**
	- Persona do Pluto (tom acessível/brincalhão).
	- Política de segurança (anti-alucinação).
	- Regra de grounding: não recomendar produtos fora do catálogo.

2. **Contexto dinâmico por consulta (RAG leve):**
	- Para perguntas sobre finanças pessoais: perfil + transações + metas + catálogo.
	- Para perguntas de mercado/sentimento: recortes relevantes dos datasets HF.
	- Para perguntas educativas: trechos de QA e FAQ financeiros.
	- Para perguntas de investimento (renda fixa, ETF, ações, cripto): cruzamento entre perfil do cliente + `produtos_financeiros.json` + alerta de risco obrigatório.

### Regras de Governança de Dados
- **Prioridade de fonte:**
  1) dados do cliente (`data/`) → 2) catálogo de produtos → 3) contexto HF.
- **Rastreabilidade:** toda recomendação deve indicar base de origem.
- **Escopo global:** resposta pode incluir ativos internacionais (ex.: EUA) quando houver suporte nos dados carregados e aderência ao perfil.
- **Idioma atual:** respostas em português nesta fase; internacionalização para inglês ocorrerá depois.
- **Cripto e ativos de alto risco:** abordagem educativa e conservadora; sempre incluir aviso de volatilidade alta e risco de perda de capital.

---

## Exemplo de Contexto Montado

> Mostre um exemplo de como os dados são formatados para o agente.

```
[CONTEXTO PLUTO | sessão atual | idioma: pt-BR]

Dados do Cliente (fonte: perfil_investidor.json)
- Nome: João Silva
- Perfil: Moderado
- Objetivo principal: Reserva de emergência
- Aceita risco alto: Não

Comportamento Financeiro (fonte: transacoes.csv)
- Gasto total no período: R$ X
- Categoria mais relevante: moradia
- Alerta: gasto em lazer acima da média histórica

Catálogo de Produtos Permitidos (fonte: produtos_financeiros.json)
- Tesouro Selic (renda fixa, risco baixo)
- US Treasury ETF - SGOV (renda fixa internacional, risco baixo + risco cambial)
- ETF S&P 500 - VOO (ETF de ações, risco médio-alto)
- Ação Apple - AAPL (ação individual, risco alto)
- Bitcoin - BTC (cripto, risco muito alto)

Contexto de Mercado Global (fonte: data/hf/*)
- Sentimento de notícias financeiras recentes: neutro/positivo
- Série histórica consultada: ativos com liquidez (incluindo US market)

Regras de Resposta
- Não inventar produto/taxa.
- Só recomendar itens do catálogo carregado.
- Incluir aviso educacional (não é recomendação de investimento formal).
- Em ETF/ações/cripto, incluir alerta de risco específico do ativo.
```

---

## Justificativa da Base Escolhida

Esta composição de dados faz sentido para o nosso momento porque:

- **Entrega MVP rápido:** com dados estruturados locais já prontos para personalização.
- **Escala para o global:** com datasets financeiros públicos para ampliar cobertura além de um único país.
- **Mantém segurança:** catálogo fechado + rastreabilidade de fonte evita alucinações críticas.
- **Cobre classes-chave de investimento:** renda fixa, mercado acionário, ETFs e cripto com política de risco explícita.
- **Suporta evolução da marca:** alinhado ao posicionamento Uill MVP (performance, consistência e decisões de qualidade).
