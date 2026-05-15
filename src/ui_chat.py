"""Chat timeline, feedback UI, and user-turn handling for Streamlit."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from context_builder import build_context, build_llm_messages, build_recent_messages
from finance_knowledge import (
    build_finance_knowledge_context,
    extract_transactions_from_message,
    is_transaction_message,
)
from llm import call_ollama, call_primary_llm
from market import (
    detect_unknown_assets,
    extract_market_symbols,
    fetch_market_quotes,
    format_market_snapshot,
    get_known_assets,
    is_price_query,
)
from profile import extract_profile_updates
from response_processing import (
    apply_post_response_validation,
    enforce_response_language,
    fallback_offline_response,
    normalize_assistant_text,
)


def render_chat_history_and_feedback(
    *,
    texts: dict[str, Any],
    auth_user_id: str | None,
    auth_access_token: str | None,
    log_event_fn: Callable[[str, dict[str, Any] | None], None],
    save_persistent_state_fn: Callable[..., bool],
    build_persisted_snapshot_fn: Callable[[Any], dict[str, Any]],
) -> None:
    """Render existing messages and feedback controls for latest assistant answer."""
    last_assistant_index = max(
        (
            index
            for index, message in enumerate(st.session_state.messages)
            if message["role"] == "assistant"
        ),
        default=-1,
    )

    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and index == last_assistant_index:
                st.caption(texts["feedback_title"])
                fb_key = f"feedback_{index}"
                already_sent = st.session_state.feedback.get(f"{fb_key}_sent", False)
                if not already_sent:
                    fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 4])
                    with fb_col1:
                        thumb_up = st.button(
                            texts["feedback_positive"], key=f"fb_up_{index}"
                        )
                    with fb_col2:
                        thumb_down = st.button(
                            texts["feedback_negative"], key=f"fb_down_{index}"
                        )
                    if thumb_up or thumb_down:
                        st.session_state.feedback[f"{fb_key}_vote"] = (
                            "positive" if thumb_up else "negative"
                        )
                        st.session_state.feedback[f"{fb_key}_show_form"] = True
                        st.rerun()

                    if st.session_state.feedback.get(f"{fb_key}_show_form"):
                        with st.form(key=f"fb_form_{index}", clear_on_submit=True):
                            rating = st.slider(
                                texts["feedback_rating_label"],
                                min_value=1,
                                max_value=5,
                                value=(
                                    4
                                    if st.session_state.feedback.get(f"{fb_key}_vote")
                                    == "positive"
                                    else 2
                                ),
                                key=f"fb_rating_{index}",
                            )
                            comment = st.text_area(
                                texts["feedback_comment_label"],
                                placeholder=texts["feedback_comment_placeholder"],
                                height=80,
                                key=f"fb_comment_{index}",
                            )
                            if st.form_submit_button(texts["feedback_submit"]):
                                vote = st.session_state.feedback.get(
                                    f"{fb_key}_vote", "positive"
                                )
                                st.session_state.feedback[fb_key] = vote
                                st.session_state.feedback[f"{fb_key}_rating"] = rating
                                st.session_state.feedback[f"{fb_key}_comment"] = comment
                                st.session_state.feedback[f"{fb_key}_sent"] = True
                                st.session_state.feedback_notice = texts[
                                    "feedback_saved"
                                ]
                                log_event_fn(
                                    "feedback_submitted",
                                    {
                                        "message_index": index,
                                        "vote": vote,
                                        "rating": rating,
                                        "comment": comment[:300] if comment else "",
                                    },
                                )
                                save_persistent_state_fn(
                                    build_persisted_snapshot_fn(st.session_state),
                                    auth_user_id,
                                    auth_access_token,
                                )
                                st.rerun()
                else:
                    vote_label = (
                        texts["feedback_positive"]
                        if st.session_state.feedback.get(f"{fb_key}_vote") == "positive"
                        else texts["feedback_negative"]
                    )
                    rating_val = st.session_state.feedback.get(f"{fb_key}_rating", "")
                    comment_val = st.session_state.feedback.get(f"{fb_key}_comment", "")
                    summary = f"{vote_label} {rating_val}/5"
                    if comment_val:
                        summary += (
                            f" · _{comment_val[:60]}"
                            f"{'…' if len(comment_val) > 60 else ''}_"
                        )
                    st.caption(f"{texts['feedback_saved']} {summary}")


def process_user_turn(
    *,
    texts: dict[str, Any],
    language: str,
    products: list[dict[str, Any]],
    history: pd.DataFrame,
    tax_knowledge: dict[str, Any],
    system_prompt: str,
    ollama_ready: bool,
    auth_user_id: str | None,
    auth_access_token: str | None,
    log_event_fn: Callable[[str, dict[str, Any] | None], None],
    save_persistent_state_fn: Callable[..., bool],
    build_persisted_snapshot_fn: Callable[[Any], dict[str, Any]],
) -> None:
    """Process user input from chat box and append assistant response."""
    user_text = st.chat_input(texts["chat_placeholder"])
    if not user_text:
        return

    log_event_fn(
        "user_message_received",
        {
            "language": language,
            "chat_mode": st.session_state.chat_mode,
            "message_length": len(user_text),
        },
    )

    profile_updates = extract_profile_updates(user_text, st.session_state.user_profile)
    profile_updated = False
    if profile_updates:
        profile_updated = True
        st.session_state.user_profile.update(profile_updates)
        log_event_fn("profile_updated", {"fields": list(profile_updates.keys())})

    transaction_notice = ""
    transactions_recorded = False
    if is_transaction_message(user_text):
        transactions = extract_transactions_from_message(user_text)
        if transactions:
            transactions_recorded = True
            txn_row = pd.DataFrame(transactions)
            txn_row["data"] = pd.to_datetime(txn_row["data"], errors="coerce")
            txn_row["valor"] = pd.to_numeric(txn_row["valor"], errors="coerce").fillna(
                0.0
            )
            st.session_state.user_transactions = pd.concat(
                [st.session_state.user_transactions, txn_row], ignore_index=True
            )
            current_wealth_value = float(
                st.session_state.user_profile.get("patrimonio_atual") or 0.0
            )
            for txn in transactions:
                if txn["tipo"] == "entrada":
                    current_wealth_value += float(txn["valor"])
                else:
                    current_wealth_value -= float(txn["valor"])
            st.session_state.user_profile["patrimonio_atual"] = max(
                current_wealth_value, 0.0
            )

            notice_lines = []
            for txn in transactions:
                log_event_fn("transaction_recorded", txn)
                tipo_label = "Income" if txn["tipo"] == "entrada" else "Expense"
                notice_lines.append(
                    texts["transaction_recorded"].format(
                        tipo=tipo_label,
                        valor=txn["valor"],
                        categoria=txn["categoria"],
                        data=txn["data"],
                    )
                )
            transaction_notice = "\n".join(notice_lines)

    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    if transaction_notice:
        st.info(transaction_notice)
        st.caption(texts["transaction_recorded_caption"])

    known_assets = get_known_assets(products)
    unknown_assets = detect_unknown_assets(user_text, known_assets)

    market_snapshot = ""
    if is_price_query(user_text):
        symbols = extract_market_symbols(user_text, known_assets)
        quotes = fetch_market_quotes(symbols)
        market_snapshot = format_market_snapshot(quotes, language)

    context = build_context(
        st.session_state.user_profile,
        st.session_state.user_transactions,
        products,
        history,
    )
    finance_knowledge_context = build_finance_knowledge_context(
        user_text=user_text,
        profile=st.session_state.user_profile,
        products=products,
        tax_knowledge=tax_knowledge,
        language=language,
    )
    conversation_messages = build_recent_messages(st.session_state.messages[:-1])
    llm_messages = build_llm_messages(
        system_prompt=system_prompt,
        context=context,
        user_text=user_text,
        conversation_messages=conversation_messages,
        language=language,
        market_snapshot=market_snapshot,
        finance_knowledge_context=finance_knowledge_context,
    )

    answer, rate_limit_hit, primary_status, primary_provider = call_primary_llm(
        llm_messages
    )
    st.session_state.llm_debug_status = primary_status
    st.session_state.rate_limit_notice = (
        texts["rate_limit_notice"] if rate_limit_hit else ""
    )
    if rate_limit_hit:
        log_event_fn("primary_rate_limited", {"provider": primary_provider})

    if not answer and ollama_ready:
        answer = call_ollama(llm_messages)
        if answer:
            log_event_fn("answer_source", {"source": "ollama"})
            st.session_state.llm_debug_status = (
                st.session_state.llm_debug_status + " | fallback: ollama"
            )

    if not answer:
        answer = fallback_offline_response(user_text, language)
        log_event_fn("answer_source", {"source": "fallback"})
        st.session_state.llm_debug_status = (
            st.session_state.llm_debug_status + " | fallback: offline"
        )
    elif not rate_limit_hit:
        log_event_fn("answer_source", {"source": primary_provider})

    answer = apply_post_response_validation(
        response_text=answer,
        profile=st.session_state.user_profile,
        user_text=user_text,
        unknown_assets=unknown_assets,
        language=language,
        rate_limit_hit=rate_limit_hit,
        profile_updates=profile_updates,
    )

    if is_price_query(user_text) and market_snapshot:
        if "snapshot" not in answer.lower() and "quote" not in answer.lower():
            answer += "\n\n" + market_snapshot

    answer = enforce_response_language(answer, language)
    answer = normalize_assistant_text(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)

    if not save_persistent_state_fn(
        build_persisted_snapshot_fn(st.session_state),
        auth_user_id,
        auth_access_token,
    ):
        st.warning(texts["state_save_error"])
        log_event_fn("state_save_error")

    # The dashboard is rendered before chat processing in this run, so force a
    # rerender when transactions were recorded to refresh top metrics instantly.
    if transactions_recorded or profile_updated:
        st.rerun()
