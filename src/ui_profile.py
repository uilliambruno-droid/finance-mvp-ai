"""Profile intake and dashboard UI for Streamlit."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from profile import (
    apply_profile_form_submission,
    format_goal_timeline,
    format_profile_summary,
    goal_progress,
    profile_completion,
)
from state import normalize_transactions


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _monthly_average_by_type(transactions: pd.DataFrame, tx_type: str) -> float:
    if transactions.empty:
        return 0.0

    tx = transactions.copy()
    tx["data"] = pd.to_datetime(tx["data"], errors="coerce")
    tx["valor"] = pd.to_numeric(tx["valor"], errors="coerce").fillna(0.0)
    tx = tx.dropna(subset=["data"])
    if tx.empty:
        return 0.0

    filtered = tx[tx["tipo"] == tx_type].copy()
    if filtered.empty:
        return 0.0

    filtered["year_month"] = filtered["data"].dt.to_period("M").astype(str)
    monthly_totals = filtered.groupby("year_month", as_index=False)["valor"].sum()
    if monthly_totals.empty:
        return 0.0
    return float(monthly_totals["valor"].mean())


def _apply_csv_financial_updates(transactions: pd.DataFrame) -> dict[str, float]:
    tx = transactions.copy()
    tx["valor"] = pd.to_numeric(tx["valor"], errors="coerce").fillna(0.0)

    total_income = float(tx.loc[tx["tipo"] == "entrada", "valor"].sum())
    total_expenses = float(tx.loc[tx["tipo"] == "saida", "valor"].sum())
    net_flow = total_income - total_expenses

    profile = st.session_state.user_profile
    current_wealth = _safe_float(profile.get("patrimonio_atual"), 0.0)
    profile["patrimonio_atual"] = round(max(current_wealth + net_flow, 0.0), 2)

    avg_monthly_expenses = _monthly_average_by_type(tx, "saida")
    avg_monthly_income = _monthly_average_by_type(tx, "entrada")

    if avg_monthly_expenses > 0:
        profile["gastos_mensais"] = round(avg_monthly_expenses, 2)
        profile["tem_gastos"] = True
    if avg_monthly_income > 0:
        profile["renda_mensal"] = round(avg_monthly_income, 2)
        profile["sem_renda"] = False

    st.session_state.user_profile = profile
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_flow": net_flow,
    }


def _render_sticky_spending_plan(texts: dict[str, Any]) -> None:
    if len(st.session_state.messages) < 10:
        return

    title = texts.get("spending_plan_title", "Spending Plan (Pinned)")
    no_income_text = texts.get(
        "spending_plan_no_income",
        "No monthly income mapped yet. Prioritize essentials, cut recurring costs, and build cash buffer first.",
    )
    income_label = texts.get("spending_plan_income", "Income")
    expenses_label = texts.get("spending_plan_expenses", "Expenses")
    essentials_label = texts.get("spending_plan_essentials", "Essentials cap")
    lifestyle_label = texts.get("spending_plan_lifestyle", "Lifestyle cap")
    reserve_label = texts.get("spending_plan_reserve", "Reserve/invest")

    profile = st.session_state.user_profile
    income = _safe_float(profile.get("renda_mensal"), 0.0)
    expenses = _safe_float(profile.get("gastos_mensais"), 0.0)

    if income <= 0:
        plan_text = no_income_text
    else:
        essentials_cap = round(income * 0.6, 2)
        lifestyle_cap = round(income * 0.2, 2)
        reserve_target = round(max(income - expenses, 0.0), 2)
        plan_text = (
            f"{income_label}: R$ {income:,.2f} | "
            f"{expenses_label}: R$ {expenses:,.2f} | "
            f"{essentials_label}: R$ {essentials_cap:,.2f} | "
            f"{lifestyle_label}: R$ {lifestyle_cap:,.2f} | "
            f"{reserve_label}: R$ {reserve_target:,.2f}"
        )

    st.markdown(
        f"""
        <div style="position:sticky;top:.6rem;z-index:999;
                    background:rgba(15,23,42,.97);border:1px solid #334155;
                    border-radius:12px;padding:.75rem 1rem;margin:.35rem 0 .7rem 0;
                    box-shadow:0 10px 30px rgba(2,6,23,.35);">
          <div style="color:#93c5fd;font-size:.78rem;font-weight:700;letter-spacing:.04em;
                      text-transform:uppercase;margin-bottom:.2rem;">
            {title}
          </div>
          <div style="color:#e2e8f0;font-size:.95rem;line-height:1.4;">{plan_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_intake_gate(
    *,
    texts: dict[str, Any],
    language: str,
    auth_user_id: str | None,
    auth_access_token: str | None,
    log_event_fn: Callable[[str, dict[str, Any] | None], None],
    save_persistent_state_fn: Callable[..., bool],
    build_persisted_snapshot_fn: Callable[[Any], dict[str, Any]],
    build_consultant_welcome_fn: Callable[[dict[str, Any], str], str],
) -> None:
    """Render profile intake form when profile is not ready and stop execution."""
    if st.session_state.profile_ready:
        return

    st.markdown(
        """
                    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                    border-radius:16px;padding:2rem 2.5rem 1.5rem 2.5rem;margin-bottom:1.5rem;
                                            border:1px solid #0f3460;">
                        <h2 style="margin:0 0 .3rem 0;color:#e2e8f0;">🪐 Pluto Finance AI</h2>
                        <p style="margin:0;color:#94a3b8;font-size:.95rem;">
                            Fill your profile once - Pluto unlocks chat already knowing who you are and what you need.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    style_options = [
        ("Conservative", texts["intake_profile_conservative"]),
        ("Moderate", texts["intake_profile_moderate"]),
        ("Aggressive", texts["intake_profile_aggressive"]),
    ]
    style_labels = [label for _, label in style_options]
    style_lookup = {label: value for value, label in style_options}

    with st.form("profile_intake_form", clear_on_submit=False):
        st.markdown("#### Identification")
        name = st.text_input(
            texts["intake_name"] + " *",
            value=st.session_state.user_profile.get("nome", ""),
            placeholder="How should Pluto call you?",
        )

        st.markdown("---")
        st.markdown("#### Income")
        income_source = st.text_input(
            texts["intake_income_source"],
            value=st.session_state.user_profile.get("fonte_renda", ""),
            placeholder="Ex: salary, freelance, own business",
        )
        income = st.number_input(
            texts["intake_income"],
            min_value=0.0,
            value=float(st.session_state.user_profile.get("renda_mensal") or 0.0),
            step=100.0,
            format="%.2f",
        )

        st.markdown("---")
        st.markdown("#### Profile and Spending")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            investor_style_label = st.selectbox(
                texts["intake_profile"] + " *",
                options=style_labels,
                index=style_labels.index(
                    {
                        "Conservative": texts["intake_profile_conservative"],
                        "Moderate": texts["intake_profile_moderate"],
                        "Aggressive": texts["intake_profile_aggressive"],
                    }.get(
                        st.session_state.user_profile.get("perfil_investidor")
                        or "Moderate",
                        texts["intake_profile_moderate"],
                    )
                ),
            )
        with col_p2:
            spending = st.number_input(
                texts["intake_spending"],
                min_value=0.0,
                value=float(st.session_state.user_profile.get("gastos_mensais") or 0.0),
                step=100.0,
                format="%.2f",
            )

        st.markdown("---")
        st.markdown("#### Wealth Goal")
        wealth_col1, wealth_col2 = st.columns(2)
        with wealth_col1:
            current_wealth = st.number_input(
                texts["intake_current_wealth"],
                min_value=0.0,
                value=float(
                    st.session_state.user_profile.get("patrimonio_atual") or 0.0
                ),
                step=500.0,
                format="%.2f",
            )
        with wealth_col2:
            target_wealth = st.number_input(
                texts["intake_target_wealth"],
                min_value=0.0,
                value=float(
                    st.session_state.user_profile.get("meta_patrimonial") or 0.0
                ),
                step=1000.0,
                format="%.2f",
            )
        target_deadline_months = int(
            st.number_input(
                texts["intake_target_deadline_months"],
                min_value=1,
                value=int(st.session_state.user_profile.get("prazo_meta_meses") or 24),
                step=1,
                format="%d",
            )
        )
        notes = st.text_area(
            texts["intake_notes"],
            value=st.session_state.user_profile.get("observacoes", ""),
            height=60,
            placeholder="Anything else Pluto should know about you?",
        )

        st.markdown(" ")
        submit = st.form_submit_button(
            texts["intake_submit"],
            use_container_width=True,
            type="primary",
        )

    if submit:
        all_fields_filled = all(
            [
                bool(name.strip()),
                bool(income_source.strip()),
                income > 0,
                bool(investor_style_label.strip()),
                spending > 0,
                current_wealth >= 0,
                target_wealth > 0,
                target_deadline_months > 0,
            ]
        )

        if not all_fields_filled:
            st.warning(texts["intake_all_required_warning"])
            st.stop()

        stored_profile = apply_profile_form_submission(
            name=name,
            income=income,
            income_source=income_source,
            investor_style=style_lookup[investor_style_label],
            spending=spending,
            has_spending=True,
            current_wealth=current_wealth,
            target_wealth=target_wealth,
            target_deadline_months=target_deadline_months,
            notes=notes,
        )
        if not stored_profile["nome"] or not stored_profile["perfil_investidor"]:
            st.warning(texts["intake_missing_warning"])
        elif stored_profile["meta_patrimonial"] and not stored_profile.get(
            "prazo_meta_meses"
        ):
            st.warning(texts["intake_deadline_warning"])
        else:
            if not stored_profile["renda_mensal"] and not stored_profile["sem_renda"]:
                stored_profile["sem_renda"] = True
            st.session_state.user_profile = stored_profile
            st.session_state.profile_ready = True
            welcome_msg = build_consultant_welcome_fn(stored_profile, language)
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]
            st.session_state.rate_limit_notice = ""
            log_event_fn(
                "profile_form_submitted", {"fields": list(stored_profile.keys())}
            )
            save_persistent_state_fn(
                build_persisted_snapshot_fn(st.session_state),
                auth_user_id,
                auth_access_token,
            )
            st.rerun()

    st.stop()


def render_profile_dashboard_and_tools(
    *,
    texts: dict[str, Any],
    language: str,
    auth_user_id: str | None,
    auth_access_token: str | None,
    log_event_fn: Callable[[str, dict[str, Any] | None], None],
    save_persistent_state_fn: Callable[..., bool],
    build_persisted_snapshot_fn: Callable[[Any], dict[str, Any]],
    build_consultant_welcome_fn: Callable[[dict[str, Any], str], str],
) -> None:
    """Render profile dashboard, CSV upload, and summary capsule."""
    completion = profile_completion(st.session_state.user_profile)
    interaction_count = len(
        [
            message
            for message in st.session_state.messages
            if message.get("role") == "user"
        ]
    )
    transaction_count = int(len(st.session_state.user_transactions))

    profile = st.session_state.user_profile
    name = profile.get("nome", "-")
    style_raw = profile.get("perfil_investidor", "-")
    style = {
        "Conservative": "Conservative",
        "Moderate": "Moderate",
        "Aggressive": "Aggressive",
    }.get(style_raw, style_raw)
    income_raw = profile.get("renda_mensal")
    no_income = profile.get("sem_renda", False)
    if no_income or not income_raw:
        income_str = "No income"
    else:
        income_str = f"R$ {float(income_raw):,.0f}/mo"

    current_wealth, target_wealth, goal_progress_value = goal_progress(profile)
    deadline_months = profile.get("prazo_meta_meses")
    deadline_str = format_goal_timeline(deadline_months, language)

    missing = None
    monthly_needed = None
    monthly_suffix = "/mo"
    if current_wealth is not None and target_wealth is not None:
        missing = max(target_wealth - current_wealth, 0.0)
        if deadline_months not in (None, "", 0):
            monthly_needed = missing / float(deadline_months)

    bar_width = completion
    progress_width = goal_progress_value if target_wealth else bar_width

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
                    border-radius:14px;padding:1.1rem 1.5rem;margin-bottom:1rem;
                    border:1px solid #334155;display:flex;flex-wrap:wrap;gap:1.2rem;
                    align-items:center;">
          <div style="flex:1 1 120px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Name</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{name}</div>
          </div>
          <div style="flex:1 1 120px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Profile</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{style}</div>
          </div>
          <div style="flex:1 1 150px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Income</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{income_str}</div>
          </div>
          <div style="flex:1 1 150px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_current_label']}</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {current_wealth:,.0f}' if current_wealth is not None else '-')}</div>
          </div>
          <div style="flex:1 1 150px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_target_label']}</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {target_wealth:,.0f}' if target_wealth is not None else '-')}</div>
          </div>
          <div style="flex:1 1 150px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_missing_label']}</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {missing:,.0f}' if missing is not None else '-')}</div>
          </div>
          <div style="flex:1 1 180px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['intake_target_deadline_label']}</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{deadline_str}</div>
          </div>
          <div style="flex:1 1 180px;">
                        <div
                            style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;"
                        >{texts['intake_target_monthly_needed_label']}</div>
                        <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">
                            {(f'R$ {monthly_needed:,.0f}{monthly_suffix}' if monthly_needed is not None else '-')}
                        </div>
          </div>
          <div style="flex:1 1 100px;text-align:right;">
                        <div
                            style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;"
                        >{texts['intake_goal_progress']}</div>
            <div style="background:#1e293b;border-radius:99px;height:6px;margin-top:4px;">
                            <div
                                style="background:#38bdf8;width:{progress_width}%;height:6px;border-radius:99px;"
                            ></div>
            </div>
                        <div style="color:#38bdf8;font-size:.78rem;margin-top:2px;">
                            {goal_progress_value if target_wealth else bar_width}%
                        </div>
          </div>
          <div style="flex:1 1 80px;text-align:center;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Messages</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:1.1rem;">{interaction_count}</div>
          </div>
          <div style="flex:1 1 80px;text-align:center;">
                        <div
                            style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;"
                        >Transactions</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:1.1rem;">{transaction_count}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(texts["edit_profile"], key="btn_edit_profile"):
        st.session_state.profile_ready = False
        st.rerun()

    with st.expander(texts["csv_title"], expanded=False):
        st.caption(texts["csv_caption"])
        uploaded_file = st.file_uploader(
            texts["upload_label"], type=["csv"], help=texts["upload_help"]
        )
        if uploaded_file is not None:
            try:
                upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
                if (
                    st.session_state.get("last_csv_upload_signature")
                    == upload_signature
                ):
                    st.info(
                        texts.get(
                            "finance_already_updated",
                            "This CSV was already processed and your finance status is up to date.",
                        )
                    )
                else:
                    uploaded_transactions = pd.read_csv(uploaded_file)
                    st.session_state.user_transactions = normalize_transactions(
                        uploaded_transactions
                    )
                    summary = _apply_csv_financial_updates(
                        st.session_state.user_transactions
                    )
                    st.session_state.last_csv_upload_signature = upload_signature

                    financial_message = texts.get(
                        "finance_updated_message",
                        "Financial status updated from CSV. "
                        "Income: R$ {income:,.2f}, expenses: R$ {expenses:,.2f}, "
                        "net flow: R$ {net:,.2f}.",
                    ).format(
                        income=summary["total_income"],
                        expenses=summary["total_expenses"],
                        net=summary["net_flow"],
                    )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": financial_message}
                    )

                    st.success(texts["upload_success"])
                    st.info(financial_message)
                    log_event_fn(
                        "transactions_uploaded",
                        {
                            "rows": int(len(st.session_state.user_transactions)),
                            "total_income": round(summary["total_income"], 2),
                            "total_expenses": round(summary["total_expenses"], 2),
                            "net_flow": round(summary["net_flow"], 2),
                        },
                    )
                    save_persistent_state_fn(
                        build_persisted_snapshot_fn(st.session_state),
                        auth_user_id,
                        auth_access_token,
                    )
                    st.rerun()
            except Exception:
                st.error(texts["upload_error"])
                log_event_fn("transactions_upload_error")

    profile_summary = format_profile_summary(st.session_state.user_profile, language)
    if profile_summary:
        st.caption(f"{texts['profile_summary']}: {profile_summary}")
    else:
        st.caption(f"{texts['profile_summary']}: {texts['profile_empty']}")

    _render_sticky_spending_plan(texts)

    if not st.session_state.messages:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": build_consultant_welcome_fn(
                    st.session_state.user_profile, language
                ),
            }
        ]

    if st.session_state.rate_limit_notice:
        st.warning(st.session_state.rate_limit_notice)
    if st.session_state.llm_debug_status:
        st.caption(f"LLM debug: {st.session_state.llm_debug_status}")
    if st.session_state.feedback_notice:
        st.success(st.session_state.feedback_notice)
        st.session_state.feedback_notice = ""
