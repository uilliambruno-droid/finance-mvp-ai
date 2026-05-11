# Código da Aplicação

Esta pasta contém a parte funcional do Pluto em Streamlit.

## Estrutura Atual

```
src/
├── app.py      # App Streamlit funcional (dashboard + chat Pluto)
└── README.md   # Guia de execução
```

## O que o app já faz

- Carrega dados de `data/` (`transacoes.csv`, `perfil_investidor.json`, `produtos_financeiros.json`, `historico_atendimento.csv`).
- Exibe indicadores financeiros básicos no topo.
- Oferece chat do Pluto com:
	- fallback local (sem LLM),
	- integração opcional com Ollama local,
	- alertas automáticos de risco para ETF/ações/cripto,
	- bloqueio de recomendação para ativos fora do catálogo.

## Como rodar

```bash
cd /Users/uilliamsantos/Documents/mvp-finance-ai
source venv/bin/activate
streamlit run src/app.py
```

## Usando com Ollama (opcional, custo zero de API)

1. Instale o Ollama: `https://ollama.com/download`
2. Puxe um modelo local (exemplo):

```bash
ollama pull qwen2.5:7b-instruct
```

3. Inicie o Ollama (se necessário) e rode o Streamlit.
4. No app, ative `Usar Ollama local` na barra lateral.

Se o Ollama estiver offline, o Pluto continua funcionando com fallback local.

## O que é Ollama

Ollama é uma ferramenta para rodar modelos LLM localmente no seu computador.

- Não depende de API paga por requisição.
- Mantém dados localmente.
- Permite trocar o modelo facilmente (`qwen`, `llama`, etc.).

No nosso caso, ele é o caminho mais prático para manter o MVP com custo de API zero.
