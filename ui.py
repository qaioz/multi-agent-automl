"""Streamlit viewer for Multi-Agent AutoML Team runs.

    streamlit run ui.py

A read-only window onto a run dir (DESIGN §5): it renders events.jsonl and the
stage artifacts — nothing here influences the agents, and replay needs no API
key. Live mode (u15) reuses the same renderer on a tailing loop.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from automl_team import events as ev
from automl_team.events import read_events

st.set_page_config(page_title="Multi-Agent AutoML Team", page_icon="🤖", layout="wide")

_STAGE_ICONS = {"ok": "✅", "failed": "❌", "running": "⚙️", "pending": "⬜"}


def list_runs() -> list[Path]:
    dirs = [
        d
        for root in (Path("examples"), Path("runs"))
        if root.exists()
        for d in root.iterdir()
        if (d / "events.jsonl").exists()
    ]
    return sorted(dirs, key=lambda d: (d / "events.jsonl").stat().st_mtime, reverse=True)


def stage_statuses(events: list[dict]) -> dict[str, str]:
    meta = next((e for e in events if e["type"] == ev.RUN_META), None)
    statuses = {name: "pending" for name in (meta["payload"].get("stages", []) if meta else [])}
    for e in events:
        if e["type"] == ev.STAGE_START:
            statuses[e["payload"]["stage"]] = "running"
        elif e["type"] == ev.STAGE_END:
            statuses[e["payload"]["stage"]] = e["payload"].get("status", "ok")
    return statuses


def render_stepper(events: list[dict]) -> None:
    statuses = stage_statuses(events)
    if not statuses:
        return
    cols = st.columns(len(statuses))
    for col, (name, status) in zip(cols, statuses.items()):
        col.markdown(f"### {_STAGE_ICONS.get(status, '⬜')} {name.replace('_', ' ')}")


def render_transcript(events: list[dict]) -> None:
    for e in events:
        agent, t, p = e.get("agent", "?"), e["type"], e.get("payload", {})
        if t == ev.REASONING:
            with st.chat_message("assistant"):
                st.markdown(f"**💭 {agent}** — {p.get('text', '')}")
        elif t == ev.TOOL_CALL:
            args = json.dumps(p.get("args", {}), ensure_ascii=False)
            st.markdown(f"🧰 `{agent}` → **{p.get('tool')}**`({args[:300]})`")
        elif t == ev.TOOL_RESULT:
            result = str(p.get("result", ""))
            with st.expander(f"↩ {p.get('tool')} result ({len(result)} chars)"):
                st.code(result[:4000], language="json")
        elif t == ev.EXECUTION:
            rc = p.get("returncode")
            label = f"⚙ execution #{p.get('iteration')} — returncode {rc}"
            with st.expander(label, expanded=bool(rc)):
                if p.get("stdout"):
                    st.code(p["stdout"][:4000], language="text")
                if (p.get("stderr") or "").strip():
                    st.error("stderr")
                    st.code(p["stderr"][:4000], language="text")
        elif t == ev.ITERATION_METRICS:
            st.markdown(f"📊 iteration {p.get('iteration')}: "
                        f"`{json.dumps(p.get('metrics', {}), ensure_ascii=False)}`")
        elif t == ev.HANDOFF:
            st.success(f"🤝 {agent} handoff → `{p.get('csv_path', '')}`")
        elif t == ev.ERROR:
            st.warning(f"❗ {p.get('message', '')}")
        elif t == ev.STAGE_START:
            st.divider()
            st.subheader(f"stage: {p.get('stage', '?')}")


def render_data_tabs(run_dir: Path) -> None:
    frames = [
        ("Raw", run_dir / "00_raw_data.csv"),
        ("Clean", run_dir / "01_clean_data.csv"),
        ("Engineered", run_dir / "02_engineered_data.csv"),
    ]
    available = [(label, p) for label, p in frames if p.exists()]
    if not available:
        st.info("no dataframes in this run yet")
        return
    for tab, (label, path) in zip(st.tabs([label for label, _ in available]), available):
        with tab:
            df = pd.read_csv(path)
            st.caption(f"{df.shape[0]} rows × {df.shape[1]} cols (first 200 rows shown)")
            st.dataframe(df.head(200))


def render_trainer(run_dir: Path, events: list[dict]) -> None:
    history_path = run_dir / "03_metrics_history.json"
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
        if history:
            rows = [{"iteration": h["iteration"], **h.get("metrics", {})} for h in history]
            df = pd.DataFrame(rows).set_index("iteration")
            numeric = df.select_dtypes(include="number")
            st.markdown("**Metrics per iteration** (from the agent's own executed output)")
            st.line_chart(numeric)
            st.dataframe(df)
    executions = [e for e in events if e["type"] == ev.EXECUTION]
    if not executions:
        st.info("no trainer executions in this run yet")
        return
    for e in executions:
        p = e["payload"]
        rc = p.get("returncode")
        with st.expander(f"execution #{p.get('iteration')} — returncode {rc}",
                         expanded=False):
            st.code(p.get("stdout") or "(no stdout)", language="text")
            if (p.get("stderr") or "").strip():
                st.error("stderr")
                st.code(p["stderr"], language="text")


def render_reports(run_dir: Path) -> None:
    reports = [
        ("🧹 Cleaner", run_dir / "01_cleaner_report.md"),
        ("🏗 Strategy", run_dir / "02_strategy_report.md"),
        ("🤖 Trainer", run_dir / "03_trainer_report.md"),
        ("📄 Final report", run_dir / "report.md"),
    ]
    available = [(label, p) for label, p in reports if p.exists()]
    if not available:
        st.info("no reports in this run yet")
        return
    for tab, (label, path) in zip(st.tabs([label for label, _ in available]), available):
        with tab:
            st.markdown(path.read_text(encoding="utf-8"))


def render_run(run_dir: Path) -> None:
    events = read_events(run_dir / "events.jsonl")
    st.title("🤖 Multi-Agent AutoML Team")
    st.caption(f"run: `{run_dir}` · {len(events)} events")
    render_stepper(events)
    tab_t, tab_d, tab_l, tab_r = st.tabs(
        ["📜 Transcript", "🗂 Data", "📈 Trainer loop", "📑 Reports"]
    )
    with tab_t:
        render_transcript(events)
    with tab_d:
        render_data_tabs(run_dir)
    with tab_l:
        render_trainer(run_dir, events)
    with tab_r:
        render_reports(run_dir)


def main() -> None:
    runs = list_runs()
    if not runs:
        st.title("🤖 Multi-Agent AutoML Team")
        st.info("No runs found. Produce one with:  \n"
                "`uv run python run_pipeline.py --data data/IT_Salary_Survey_EU_2020.csv`")
        return
    selected = st.sidebar.selectbox("Run", [str(p) for p in runs])
    st.sidebar.caption("Replay mode — renders a finished run; no API key needed.")
    render_run(Path(selected))


main()
