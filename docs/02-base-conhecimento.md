# Knowledge Base

## Data Sources
- data/perfil_investidor.json: User profile defaults.
- data/transacoes.csv: Transaction history.
- data/produtos_financeiros.json: Allowed product catalog.
- data/historico_atendimento.csv: Previous support history.
- data/knowledge/tax_knowledge.json: Structured tax and product rules.
- data/hf/: Curated public finance datasets for optional enrichment.

## Integration Strategy
- Core CSV and JSON files are loaded locally for deterministic grounding.
- Curated HF datasets are optional and task-dependent.
- When uncertainty is high, Pluto answers conservatively and states limits.

## Governance
- Recommendations must align with catalog entries.
- Responses include risk context for volatile assets.
- Brazil-first compliance and tax context are prioritized.
