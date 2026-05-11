# Avaliação e Métricas

## Como Avaliar o Pluto

Duas camadas de avaliação estão implementadas:

1. **Testes automatizados** — `pytest tests/` cobre extração de perfil, integridade do LLM, persistência e cenários de formulário.
2. **Feedback em tempo real** — cada resposta do Pluto exibe um formulário de feedback com: polegar 👍/👎, nota de 1–5 ⭐ e campo de texto livre. Tudo é salvo em `data/runtime/events.jsonl`.

---

## Métricas de Qualidade

| Métrica | O que avalia | Como medir |
|---------|--------------|------------|
| **Assertividade** | O Pluto respondeu o que foi perguntado? | Nota média do feedback (meta: ≥ 4/5) |
| **Segurança** | Evitou inventar produtos ou taxas? | Ausência de eventos `unknown_asset_alert` sem aviso |
| **Coerência de perfil** | Resposta coerente com o perfil do usuário? | Taxa de votos positivos pós-formulário |
| **Detecção de cenário** | Ativou guidance correto por tema? | Cobertura dos 5 cenários em `finance_knowledge.py` |
| **Registro de transação** | Detectou e salvou corretamente? | Eventos `transaction_recorded` vs. mensagens com verbo+valor |
| **Tempo de resposta** | LLM respondeu em < 5s? | Timestamp entre `user_message_received` e `answer_source` |

---

## Estrutura do Feedback Salvo

Cada feedback é um evento JSONL em `data/runtime/events.jsonl`:

```json
{
  "timestamp": "2026-05-12T14:23:00Z",
  "event": "feedback_submitted",
  "payload": {
    "message_index": 3,
    "vote": "positive",
    "rating": 4,
    "comment": "Expliquei bem a reserva de emergência, mas faltou o cálculo."
  }
}
```

---

## Cenários de Teste Implementados

| # | Pergunta de teste | Comportamento esperado |
|---|-------------------|------------------------|
| 1 | "como montar reserva de emergência?" | Ativa guidance de reserva (regra 6×, Tesouro Selic) |
| 2 | "devo quitar a dívida ou investir?" | Ativa guidance dívidas vs. investir (comparação de taxas) |
| 3 | "quanto aportar por mês?" | Ativa guidance de aportes (DCA, pay-yourself-first) |
| 4 | "quero planejar minha aposentadoria" | Ativa guidance aposentadoria (regra 25×, PGBL vs VGBL) |
| 5 | "ETF ou renda fixa?" | Ativa guidance ETF vs. RF (IR, volatilidade, perfil) |
| 6 | "gastei 150 no ifood" | Registra transação: saida / alimentação / R$ 150 |
| 7 | "recebi R$ 5.000 de salário" | Registra transação: entrada / salário / R$ 5.000 |
| 8 | "qual a previsão do tempo?" | Pluto redireciona para finanças |
| 9 | "quanto rende produto XYZ?" | Pluto admite não ter essa informação |

---

## Resultados Actuais (suite pytest)

```
tests/test_finance_knowledge.py  8 passed
tests/test_app_integration.py    5 passed
Total: 13 passed in < 1s
```

**O que está funcionando bem:**
- Perfil reconhecido imediatamente após formulário (boas-vindas personalizada)
- Detecção e registro de gastos/ganhos pelo chat
- 5 cenários financeiros com guidance estruturado
- Feedback com nota + texto livre salvo em events.jsonl
- Persistência completa de sessão (perfil + mensagens + transações)

**Próximas melhorias potenciais:**
- Dashboard de eventos (leitura do events.jsonl na UI)
- Gráfico de gastos por categoria (pandas + st.bar_chart)
- Alerta de anomalia automático quando categoria ultrapassa média

---

## Métricas Avançadas (Opcional)

Para quem quer explorar mais, algumas métricas técnicas de observabilidade também podem fazer parte da sua solução, como:

- Latência e tempo de resposta;
- Consumo de tokens e custos;
- Logs e taxa de erros.

Ferramentas especializadas em LLMs, como [LangWatch](https://langwatch.ai/) e [LangFuse](https://langfuse.com/), são exemplos que podem ajudar nesse monitoramento. Entretanto, fique à vontade para usar qualquer outra que você já conheça!