from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import app  # noqa: E402


def test_next_natural_question_guided_and_quick() -> None:
    profile = {
        "nome": "",
        "fonte_renda": "",
        "sem_renda": False,
        "renda_mensal": None,
        "perfil_investidor": "",
    }

    guided = app.next_natural_question(
        profile=profile,
        language="pt",
        has_transactions=False,
        chat_mode="guided",
    )
    quick = app.next_natural_question(
        profile=profile,
        language="pt",
        has_transactions=False,
        chat_mode="quick",
    )

    assert guided == ""
    assert quick == ""


def test_extract_profile_updates_accepts_direct_name() -> None:
    profile = app.default_user_profile()
    updates = app.extract_profile_updates("uilliam", profile)
    assert updates.get("nome") == "Uilliam"


def test_build_llm_messages_contains_brazil_scope() -> None:
    messages = app.build_llm_messages(
        system_prompt="test system",
        context="{}",
        user_text="Quero investir",
        conversation_messages=[],
        language="pt",
    )
    all_system_content = "\n".join(
        m["content"] for m in messages if m["role"] == "system"
    )
    assert "Brasil-first" in all_system_content


def test_apply_profile_form_submission_and_ready_state() -> None:
    profile = app.apply_profile_form_submission(
        name="Uilliam",
        income=5000.0,
        income_source="salário",
        investor_style="Moderado",
        spending=2500.0,
        has_spending=True,
        current_wealth=15000.0,
        target_wealth=50000.0,
        target_deadline_months=36,
        notes="",
    )

    assert profile["nome"] == "Uilliam"
    assert profile["patrimonio_atual"] == 15000.0
    assert profile["meta_patrimonial"] == 50000.0
    assert profile["prazo_meta_meses"] == 36
    assert profile["perfil_pronto"] is True
    assert app.profile_is_ready(profile) is True


def test_goal_progress_calculation() -> None:
    profile = app.default_user_profile()
    profile["patrimonio_atual"] = 25000.0
    profile["meta_patrimonial"] = 100000.0

    current, target, progress = app.goal_progress(profile)

    assert current == 25000.0
    assert target == 100000.0
    assert progress == 25


def test_format_goal_timeline_automatic_scale() -> None:
    assert app.format_goal_timeline(18, "pt") == "18 meses"
    assert app.format_goal_timeline(36, "pt") == "3 anos (36 meses)"


class DummyState:
    def __init__(self) -> None:
        self.language = "pt"
        self.chat_mode = "guided"
        self.user_profile = app.default_user_profile()
        self.messages = [
            {"role": "assistant", "content": "oi"},
            {"role": "user", "content": "me chamo uilliam"},
        ]
        self.user_transactions = app.empty_transactions()


def test_persistent_state_roundtrip(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    state_file = runtime_dir / "user_state.json"

    monkeypatch.setattr(app, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(app, "STATE_FILE", state_file)

    snapshot = app.build_persisted_snapshot(DummyState())
    assert app.save_persistent_state(snapshot)

    loaded = app.load_persistent_state()
    assert loaded.get("chat_mode") == "guided"
    assert loaded.get("language") == "pt"
    assert len(loaded.get("messages", [])) == 2


def _make_ready_profile(**overrides) -> dict:
    """Return a minimal profile that passes profile_is_ready."""
    profile = app.apply_profile_form_submission(
        name="Ana",
        income=4000.0,
        income_source="salário",
        investor_style="Moderado",
        spending=2000.0,
        has_spending=True,
        current_wealth=10000.0,
        target_wealth=50000.0,
        target_deadline_months=24,
        notes="",
    )
    profile.update(overrides)
    return profile


def test_next_natural_question_quick_mode_always_empty() -> None:
    profile = _make_ready_profile()
    result = app.next_natural_question(
        profile=profile, language="pt", has_transactions=False, chat_mode="quick"
    )
    assert result == ""


def test_next_natural_question_guided_asks_income_source_when_missing() -> None:
    profile = _make_ready_profile(fonte_renda="", sem_renda=False)
    result = app.next_natural_question(
        profile=profile, language="pt", has_transactions=False, chat_mode="guided"
    )
    assert result != ""
    assert "renda" in result.lower()


def test_next_natural_question_guided_asks_csv_when_no_transactions() -> None:
    profile = _make_ready_profile(fonte_renda="salário")
    result = app.next_natural_question(
        profile=profile, language="pt", has_transactions=False, chat_mode="guided"
    )
    assert result != ""
    assert "csv" in result.lower() or "dados" in result.lower()


def test_next_natural_question_guided_asks_goal_when_transactions_exist() -> None:
    profile = _make_ready_profile(fonte_renda="salário")
    result = app.next_natural_question(
        profile=profile, language="pt", has_transactions=True, chat_mode="guided"
    )
    assert result != ""
    assert "objetivo" in result.lower()


def test_next_natural_question_english_guided_uses_en_texts() -> None:
    profile = _make_ready_profile(fonte_renda="salary")
    result = app.next_natural_question(
        profile=profile, language="en", has_transactions=True, chat_mode="guided"
    )
    assert result != ""
    assert "goal" in result.lower() or "financial" in result.lower()


def test_texts_pt_has_all_followup_keys() -> None:
    pt = app.TEXTS["pt"]
    en = app.TEXTS["en"]
    followup_keys = [k for k in en if k.startswith("followup_")]
    for key in followup_keys:
        assert key in pt, f"TEXTS['pt'] is missing key: {key}"

