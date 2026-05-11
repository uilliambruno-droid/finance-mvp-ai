# Configurações do Projeto - Finance MVP AI

## ✅ Ambiente Preparado com Sucesso!

### 📋 O que foi instalado:

**Dependências Principais:**
- `streamlit` (1.57.0) - Interface web interativa
- `langchain` (1.2.18) - Orquestração de agentes e chains
- `langchain-core` (1.3.3) - Core do LangChain
- `langgraph` (1.1.10) - Fluxos de grafos para agentes
- `openai` (2.36.0) - Integração com API OpenAI
- `pandas` (3.0.2) - Manipulação de dados
- `python-dotenv` (1.2.2) - Carregamento de variáveis de ambiente

### 📂 Estrutura do Projeto:

```
mvp-finance-ai/
├── venv/                      # Ambiente virtual Python
├── data/                      # Dados mockados
│   ├── transacoes.csv
│   ├── historico_atendimento.csv
│   ├── perfil_investidor.json
│   └── produtos_financeiros.json
├── docs/                      # Documentação
├── src/                       # Código-fonte da aplicação
├── examples/                  # Exemplos de implementação
├── .env.example               # Template de variáveis de ambiente
├── requirements.txt           # Lista de dependências
├── .gitignore                 # Exclusões do Git
└── README.md                  # Descrição do projeto
```

### 🚀 Como Usar:

1. **Ativar o ambiente virtual:**
   ```bash
   source venv/bin/activate
   ```

2. **Configurar variáveis de ambiente:**
   ```bash
   cp .env.example .env
   # Edite .env com sua chave da OpenAI API
   ```

3. **Executar a aplicação Streamlit:**
   ```bash
   streamlit run src/app.py
   ```

4. **Instalar novas dependências (se necessário):**
   ```bash
   pip install <package_name>
   pip freeze > requirements.txt
   ```

### 📝 Próximas Etapas:

1. **Implementar documentação do agente** em `docs/01-documentacao-agente.md`
2. **Criar base de conhecimento** em `docs/02-base-conhecimento.md`
3. **Definir prompts** em `docs/03-prompts.md`
4. **Desenvolver aplicação** em `src/`
5. **Documentar métricas** em `docs/04-metricas.md`

### 🔐 Segurança:

- O arquivo `.env` será ignorado pelo Git
- Nunca commit da sua API key ou dados sensíveis
- Use `.env.example` como template para novos colaboradores

---

**Ambiente pronto para começar! 🎉**
