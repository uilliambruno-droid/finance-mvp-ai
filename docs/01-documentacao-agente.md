# Agent Documentation

## Problem
Many users struggle with daily financial decisions because advice is often generic, fragmented, and hard to apply.

## Solution
Pluto provides a guided but practical chat experience:
- Collect a minimum profile once.
- Keep context across sessions.
- Explain products, taxes, and risk in plain language.
- Track user-reported transactions and goals.

## Persona
- Friendly, practical, and direct.
- Educational tone with light humor.
- Explicitly transparent about limitations.

## Architecture Summary
1. User submits profile and messages.
2. App builds structured context from profile, transactions, and product catalog.
3. LLM generates a response under safety and grounding rules.
4. Post-validation appends risk and scope safeguards.
5. Session state and events are persisted.

## Safety Controls
- Grounding with local data.
- Unknown-asset safety notes.
- Risk disclaimers for volatile assets.
- Graceful fallback when providers fail.
- Explicit scope handling for off-topic prompts.
