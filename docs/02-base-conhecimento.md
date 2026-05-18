# Knowledge Base

## Data Sources
- data/perfil_investidor.json: User profile defaults.
- data/transacoes.csv: Transaction history.
- data/produtos_financeiros.json: Allowed product catalog.
- data/historico_atendimento.csv: Previous support history.
- data/knowledge/tax_knowledge.json: Structured tax and product rules.
- data/hf/: Curated public finance datasets for optional enrichment.

## Functional Use by Module
- finance_knowledge.py: scenario-aware educational guidance, transaction extraction from natural language, and tax/instrument context snippets.
- context_builder.py: assembles profile, transaction, and product grounding.
- ui_profile.py: CSV upload normalization and dashboard updates.
- ui_chat.py: message-level extraction and live transaction updates.

## Integration Strategy
- Core CSV and JSON files are loaded locally for deterministic grounding.
- Curated HF datasets are optional and task-dependent.
- When uncertainty is high, Pluto answers conservatively and states limits.

## Data Contracts (Expected Fields)
- Transactions: `data`, `valor`, `categoria`, `tipo`.
- Profile: income, investor profile, current net worth, target net worth, deadline.
- Product catalog: name, category, risk and market metadata.

## Governance
- Recommendations must align with catalog entries.
- Responses include risk context for volatile assets.
- Brazil-first compliance and tax context are prioritized.

## Limitations
- Knowledge quality depends on freshness of local files.
- CSV uploads with unexpected schemas are normalized best-effort.
- This is educational guidance, not legal/tax/financial advice.
