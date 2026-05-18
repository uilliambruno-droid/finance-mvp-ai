# Agent Documentation

## Problem
Many users struggle with daily financial decisions because advice is often generic, fragmented, and hard to apply.

## Solution
Pluto provides a guided but practical chat experience:
- Collect a minimum profile once.
- Keep context across sessions.
- Explain products, taxes, and risk in plain language.
- Track user-reported transactions, uploaded CSV data, and goals.

## Persona
- Friendly, practical, and direct.
- Educational tone with light humor.
- Explicitly transparent about limitations.

## Interaction Model
1. Profile-first: chat is unlocked only after minimum profile intake.
2. Context-aware chat: each response uses profile + transaction context.
3. Stateful sessions: user data is restored when persistence is available.
4. Safe guidance: responses stay in financial education scope.

## Architecture Summary
1. User sends message or uploads CSV.
2. App normalizes profile + transaction state.
3. Context builder prepares structured grounding payload.
4. LLM provider is called (OpenRouter first, optional local fallback).
5. Response-processing layer applies safeguards and output normalization.
6. UI modules render updates, feedback controls, and dashboard indicators.
7. State snapshot and event logs are persisted.

## Safety Controls
- Grounding with local data.
- Unknown-asset safety notes.
- Risk disclaimers for volatile assets.
- Graceful fallback when providers fail.
- Explicit scope handling for off-topic prompts.

## Current Scope
- Brazil-first financial education context.
- English-first response behavior.
- No brokerage actions, trades, or guaranteed-return promises.
