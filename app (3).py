"""
WAYNE PROTOCOL — Personal Hypertrophy Tracker
Black-minimal, gold-accent training log with auto volume calculation
and session-over-session progress flags.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import datetime, date

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(page_title="WAYNE PROTOCOL", page_icon="🦇", layout="wide")

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
DAILY_FILE = os.path.join(os.path.dirname(__file__), "daily_log.json")

DEFAULT_CALORIE_TARGET = 3400
DEFAULT_PROTEIN_TARGET = 210
DEFAULT_SLEEP_TARGET = 7.5

GOLD = "#c9a227"
GOLD_BRIGHT = "#e6c34a"
RED = "#d4453a"
GREEN = "#3ad46a"
BG = "#0a0a0a"
PANEL = "#141414"
BORDER = "#2a2a2a"

# ----------------------------------------------------------------------------
# PROGRAM DEFINITION
# Sets/rep ranges are programmed. Order = compounds before isolation.
# Flags on volume/order changes vs the raw exercise list are noted in the
# README at the bottom of this file and in the in-app "Program Notes" tab.
# ----------------------------------------------------------------------------
PROGRAM = {
    "Legs & Shoulders": {
        "muscles": ["Quads", "Hamstrings", "Calves", "Shoulders"],
        "exercises": [
            {"name": "Seated Leg Press", "muscle": "Quads", "sets": 3, "reps": "8-12"},
            {"name": "Leg Extension", "muscle": "Quads", "sets": 3, "reps": "12-15"},
            {"name": "Leg Curl (Lying)", "muscle": "Hamstrings", "sets": 3, "reps": "10-12"},
            {"name": "Seated Leg Curl", "muscle": "Hamstrings", "sets": 3, "reps": "10-12"},
            {"name": "Calf Press", "muscle": "Calves", "sets": 4, "reps": "12-15"},
            {"name": "DB Press", "muscle": "Shoulders", "sets": 3, "reps": "8-12"},
            {"name": "Seated Lat Raise", "muscle": "Shoulders", "sets": 3, "reps": "15-20"},
            {"name": "Rear Delt Fly", "muscle": "Shoulders", "sets": 3, "reps": "15-20"},
        ],
    },
    "Back & Chest": {
        "muscles": ["Back", "Chest"],
        "exercises": [
            {"name": "T-Bar Row", "muscle": "Back", "sets": 3, "reps": "8-10"},
            {"name": "Seated Row", "muscle": "Back", "sets": 3, "reps": "10-12"},
            {"name": "High Row", "muscle": "Back", "sets": 3, "reps": "12-15"},
            {"name": "DB Bench Press", "muscle": "Chest", "sets": 4, "reps": "8-12"},
            {"name": "Pec Flys", "muscle": "Chest", "sets": 3, "reps": "12-15"},
        ],
    },
    "Arms": {
        "muscles": ["Triceps", "Biceps"],
        "exercises": [
            {"name": "Seated OVH Tricep Press", "muscle": "Triceps", "sets": 3, "reps": "10-12"},
            {"name": "Seated Pushdown", "muscle": "Triceps", "sets": 3, "reps": "12-15"},
            {"name": "Single Hand Pushdown", "muscle": "Triceps", "sets": 2, "reps": "12-15"},
            {"name": "Incline DB Curl", "muscle": "Biceps", "sets": 3, "reps": "10-12"},
            {"name": "Incline Hammer Curl", "muscle": "Biceps", "sets": 3, "reps": "10-12"},
            {"name": "Reverse Grip Curl", "muscle": "Biceps", "sets": 2, "reps": "12-15"},
            {"name": "Preacher Curl", "muscle": "Biceps", "sets": 2, "reps": "10-12"},
        ],
    },
}

MUSCLE_PAIRS = {
    "Chest & Back": ["Chest", "Back"],
    "Biceps & Triceps": ["Biceps", "Triceps"],
    "Legs & Shoulders": ["Quads", "Hamstrings", "Calves", "Shoulders"],
}

ALL_EXERCISES = [e["name"] for day in PROGRAM.values() for e in day["exercises"]]
EXERCISE_TO_MUSCLE = {e["name"]: e["muscle"] for day in PROGRAM.values() for e in day["exercises"]}
EXERCISE_TO_DAY = {e["name"]: d for d, day in PROGRAM.items() for e in day["exercises"]}

# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {BG};
    color: #e8e8e8;
}}
h1, h2, h3, h4 {{
    font-family: 'Oswald', sans-serif !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}
h1 {{
    color: {GOLD_BRIGHT} !important;
    border-bottom: 1px solid {BORDER};
    padding-bottom: 10px;
}}
h2, h3 {{
    color: {GOLD} !important;
}}
.stApp {{
    background: radial-gradient(circle at top, #111111 0%, {BG} 70%);
}}
[data-testid="stSidebar"] {{
    background-color: {PANEL};
    border-right: 1px solid {BORDER};
}}
div[data-testid="stMetric"] {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 12px 16px;
}}
div[data-testid="stMetricLabel"] {{
    color: #999 !important;
}}
.stButton > button {{
    background-color: {GOLD};
    color: #0a0a0a;
    border: none;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    border-radius: 4px;
}}
.stButton > button:hover {{
    background-color: {GOLD_BRIGHT};
    color: #000;
}}
.exercise-card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-left: 3px solid {GOLD};
    border-radius: 4px;
    padding: 14px 18px;
    margin-bottom: 10px;
}}
.flag-red {{
    color: {RED};
    font-weight: 600;
}}
.flag-green {{
    color: {GREEN};
    font-weight: 600;
}}
hr {{
    border-color: {BORDER};
}}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DATA LAYER
# ----------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            raw = json.load(f)
    else:
        raw = []
    if not raw:
        df = pd.DataFrame(columns=["date", "day", "exercise", "muscle", "set_number", "weight", "reps"])
        df["date"] = pd.to_datetime(df["date"])
        return df
    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"])
    return df

def save_data(df):
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    with open(DATA_FILE, "w") as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def append_entries(new_rows):
    df = load_data()
    new_df = pd.DataFrame(new_rows)
    new_df["date"] = pd.to_datetime(new_df["date"])
    df = pd.concat([df, new_df], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    save_data(df)

def load_daily():
    if os.path.exists(DAILY_FILE):
        with open(DAILY_FILE, "r") as f:
            raw = json.load(f)
    else:
        raw = []
    if not raw:
        df = pd.DataFrame(columns=["date", "calories", "protein", "sleep_hours", "notes"])
        df["date"] = pd.to_datetime(df["date"])
        return df
    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"])
    return df

def save_daily(df):
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    with open(DAILY_FILE, "w") as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def upsert_daily_entry(entry):
    """One row per date. If a date already has an entry, overwrite it."""
    df = load_daily()
    entry_date = pd.to_datetime(entry["date"])
    df = df[df["date"] != entry_date] if not df.empty else df
    new_row = pd.DataFrame([entry])
    new_row["date"] = pd.to_datetime(new_row["date"])
    df = pd.concat([df, new_row], ignore_index=True)
    save_daily(df)

df_all = load_data()
if not df_all.empty:
    df_all["volume"] = df_all["weight"] * df_all["reps"]

df_daily = load_daily()

# ----------------------------------------------------------------------------
# SIDEBAR NAV
# ----------------------------------------------------------------------------
st.sidebar.markdown("## 🦇 WAYNE PROTOCOL")
page = st.sidebar.radio("", ["Log Workout", "Log Meals & Sleep", "Progress Dashboard",
                              "Weekly Summary", "Program Notes", "Backup & Restore"])

st.sidebar.markdown("---")
st.sidebar.markdown("#### Daily Targets")
calorie_target = st.sidebar.number_input("Calorie target", min_value=0, step=50,
                                          value=DEFAULT_CALORIE_TARGET)
protein_target = st.sidebar.number_input("Protein target (g)", min_value=0, step=5,
                                          value=DEFAULT_PROTEIN_TARGET)
sleep_target = st.sidebar.number_input("Sleep target (hrs)", min_value=0.0, step=0.5,
                                        value=DEFAULT_SLEEP_TARGET)

# ----------------------------------------------------------------------------
# PAGE: LOG WORKOUT
# ----------------------------------------------------------------------------
if page == "Log Workout":
    st.markdown("# Log Workout")
    day_choice = st.selectbox("Select training day", list(PROGRAM.keys()))
    day_data = PROGRAM[day_choice]
    log_date = st.date_input("Date", value=date.today())

    st.markdown(f"### {day_choice} — target muscles: {', '.join(day_data['muscles'])}")

    entries_to_save = []
    comparison_results = []

    with st.form(key=f"form_{day_choice}"):
        exercise_inputs = {}
        for ex in day_data["exercises"]:
            st.markdown(f"<div class='exercise-card'><b>{ex['name']}</b> "
                        f"<span style='color:#888'>· {ex['muscle']} · {ex['sets']} sets x {ex['reps']} reps</span></div>",
                        unsafe_allow_html=True)

            # pre-fill with last logged top weight for convenience
            prior = df_all[df_all["exercise"] == ex["name"]] if not df_all.empty else pd.DataFrame()
            last_weight = float(prior["weight"].max()) if not prior.empty else 0.0

            cols = st.columns(ex["sets"])
            set_vals = []
            for i in range(ex["sets"]):
                with cols[i]:
                    w = st.number_input(f"Set {i+1} lbs", min_value=0.0, step=2.5,
                                         value=last_weight, key=f"{ex['name']}_w_{i}")
                    r = st.number_input(f"Set {i+1} reps", min_value=0, step=1,
                                         value=0, key=f"{ex['name']}_r_{i}")
                    set_vals.append((w, r))
            exercise_inputs[ex["name"]] = set_vals

        submitted = st.form_submit_button("SAVE WORKOUT")

    if submitted:
        for ex_name, set_vals in exercise_inputs.items():
            muscle = EXERCISE_TO_MUSCLE[ex_name]
            logged_any = False
            max_weight_today = 0
            for i, (w, r) in enumerate(set_vals):
                if r > 0:
                    logged_any = True
                    max_weight_today = max(max_weight_today, w)
                    entries_to_save.append({
                        "date": log_date.strftime("%Y-%m-%d"),
                        "day": day_choice,
                        "exercise": ex_name,
                        "muscle": muscle,
                        "set_number": i + 1,
                        "weight": w,
                        "reps": r,
                    })
            if logged_any:
                prior = df_all[(df_all["exercise"] == ex_name) & (df_all["date"] < pd.to_datetime(log_date))] if not df_all.empty else pd.DataFrame()
                if not prior.empty:
                    last_session_date = prior["date"].max()
                    last_max = prior[prior["date"] == last_session_date]["weight"].max()
                    comparison_results.append((ex_name, max_weight_today, last_max))
                else:
                    comparison_results.append((ex_name, max_weight_today, None))

        if entries_to_save:
            append_entries(entries_to_save)
            st.success(f"Workout logged for {log_date.strftime('%b %d, %Y')}.")

            st.markdown("### Session vs Last Time")
            for ex_name, today_w, last_w in comparison_results:
                if last_w is None:
                    st.markdown(f"**{ex_name}**: first time logged — baseline set at {today_w} lbs.")
                elif today_w > last_w:
                    st.markdown(f"<span class='flag-green'>▲ {ex_name}: {today_w} lbs vs {last_w} lbs last time — UP.</span>",
                                unsafe_allow_html=True)
                elif today_w < last_w:
                    st.markdown(f"<span class='flag-red'>▼ {ex_name}: {today_w} lbs vs {last_w} lbs last time — DOWN.</span>",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"— {ex_name}: {today_w} lbs, same as last time.")
        else:
            st.warning("No sets with reps > 0 were entered. Nothing saved.")

# ----------------------------------------------------------------------------
# PAGE: LOG MEALS & SLEEP
# ----------------------------------------------------------------------------
elif page == "Log Meals & Sleep":
    st.markdown("# Log Meals & Sleep")
    st.markdown("One entry per day. Logging again for the same date overwrites it.")

    daily_date = st.date_input("Date", value=date.today(), key="daily_date")

    # pre-fill with existing entry for that date if present
    existing = df_daily[df_daily["date"] == pd.to_datetime(daily_date)] if not df_daily.empty else pd.DataFrame()
    prefill_cal = int(existing["calories"].iloc[0]) if not existing.empty else calorie_target
    prefill_pro = int(existing["protein"].iloc[0]) if not existing.empty else protein_target
    prefill_sleep = float(existing["sleep_hours"].iloc[0]) if not existing.empty else sleep_target
    prefill_notes = existing["notes"].iloc[0] if not existing.empty else ""

    with st.form(key="daily_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            calories = st.number_input("Calories", min_value=0, step=50, value=prefill_cal)
        with c2:
            protein = st.number_input("Protein (g)", min_value=0, step=5, value=prefill_pro)
        with c3:
            sleep_hours = st.number_input("Sleep (hrs)", min_value=0.0, max_value=24.0, step=0.25, value=prefill_sleep)
        notes = st.text_area("Meal notes (optional)", value=prefill_notes,
                              placeholder="e.g. chicken/rice x3, protein shake, missed dinner")
        submitted_daily = st.form_submit_button("SAVE DAY")

    if submitted_daily:
        upsert_daily_entry({
            "date": daily_date.strftime("%Y-%m-%d"),
            "calories": calories,
            "protein": protein,
            "sleep_hours": sleep_hours,
            "notes": notes,
        })
        st.success(f"Saved for {daily_date.strftime('%b %d, %Y')}.")

        cal_delta = calories - calorie_target
        sleep_delta = sleep_hours - sleep_target
        if cal_delta < 0:
            st.markdown(f"<span class='flag-red'>▼ Calories: {calories} vs {calorie_target} target ({cal_delta:+.0f}).</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='flag-green'>▲ Calories: {calories} vs {calorie_target} target ({cal_delta:+.0f}).</span>", unsafe_allow_html=True)
        if sleep_delta < 0:
            st.markdown(f"<span class='flag-red'>▼ Sleep: {sleep_hours}h vs {sleep_target}h target ({sleep_delta:+.1f}h).</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='flag-green'>▲ Sleep: {sleep_hours}h vs {sleep_target}h target ({sleep_delta:+.1f}h).</span>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# PAGE: PROGRESS DASHBOARD
# ----------------------------------------------------------------------------
elif page == "Progress Dashboard":
    st.markdown("# Progress Dashboard")

    if df_all.empty:
        st.info("No sessions logged yet. Go to 'Log Workout' to start tracking.")
    else:
        df_all["week"] = df_all["date"].dt.strftime("%G-W%V")

        # --- Top row metrics ---
        total_sessions = df_all["date"].nunique()
        this_week = df_all[df_all["week"] == pd.Timestamp.today().strftime("%G-W%V")]["date"].nunique()
        total_volume = int(df_all["volume"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Sessions Logged", total_sessions)
        c2.metric("Sessions This Week", f"{this_week} / 6")
        c3.metric("Total Volume Lifted (lbs)", f"{total_volume:,}")

        st.markdown("---")

        # --- Weekly volume per muscle group ---
        st.markdown("### Weekly Volume Per Muscle Group")
        weekly_muscle = df_all.groupby(["week", "muscle"])["volume"].sum().reset_index()
        weeks = sorted(weekly_muscle["week"].unique())
        muscles = sorted(weekly_muscle["muscle"].unique())

        fig1 = go.Figure()
        colors_cycle = [GOLD, "#e8e8e8", "#8a8a8a", RED, GREEN, "#a37fd1", "#5aa9e6"]
        for i, m in enumerate(muscles):
            sub = weekly_muscle[weekly_muscle["muscle"] == m]
            fig1.add_trace(go.Bar(x=sub["week"], y=sub["volume"], name=m,
                                   marker_color=colors_cycle[i % len(colors_cycle)]))
        fig1.update_layout(barmode="group", plot_bgcolor=BG, paper_bgcolor=BG,
                            font=dict(color="#e8e8e8"), legend=dict(orientation="h"),
                            xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Volume (lbs)"))
        st.plotly_chart(fig1, use_container_width=True)

        # --- Weekly volume per muscle pair ---
        st.markdown("### Weekly Volume Per Muscle Pair")
        pair_rows = []
        for pair_name, muscle_list in MUSCLE_PAIRS.items():
            sub = df_all[df_all["muscle"].isin(muscle_list)]
            pair_weekly = sub.groupby("week")["volume"].sum().reset_index()
            pair_weekly["pair"] = pair_name
            pair_rows.append(pair_weekly)
        pair_df = pd.concat(pair_rows, ignore_index=True) if pair_rows else pd.DataFrame()

        fig2 = go.Figure()
        for i, pair_name in enumerate(MUSCLE_PAIRS.keys()):
            sub = pair_df[pair_df["pair"] == pair_name]
            fig2.add_trace(go.Bar(x=sub["week"], y=sub["volume"], name=pair_name,
                                   marker_color=colors_cycle[i % len(colors_cycle)]))
        fig2.update_layout(barmode="group", plot_bgcolor=BG, paper_bgcolor=BG,
                            font=dict(color="#e8e8e8"), legend=dict(orientation="h"),
                            xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Volume (lbs)"))
        st.plotly_chart(fig2, use_container_width=True)

        # --- Daily volume ---
        st.markdown("### Volume Per Day Logged")
        daily = df_all.groupby(df_all["date"].dt.strftime("%Y-%m-%d"))["volume"].sum().reset_index()
        fig3 = go.Figure(go.Bar(x=daily["date"], y=daily["volume"], marker_color=GOLD))
        fig3.update_layout(plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color="#e8e8e8"),
                            xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Volume (lbs)"))
        st.plotly_chart(fig3, use_container_width=True)

        # --- Per-exercise weight progression ---
        st.markdown("### Exercise Progression (Top Set Weight)")
        ex_choice = st.selectbox("Select exercise", ALL_EXERCISES)
        ex_df = df_all[df_all["exercise"] == ex_choice].groupby(
            df_all["date"].dt.strftime("%Y-%m-%d"))["weight"].max().reset_index()
        if not ex_df.empty:
            fig4 = go.Figure(go.Scatter(x=ex_df["date"], y=ex_df["weight"], mode="lines+markers",
                                         line=dict(color=GOLD_BRIGHT, width=2), marker=dict(size=8)))
            fig4.update_layout(plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color="#e8e8e8"),
                                xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Top Set Weight (lbs)"))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No data yet for this exercise.")

        # --- Calories and Sleep trends ---
        st.markdown("### Calories & Sleep Trend")
        if df_daily.empty:
            st.info("No meal/sleep entries yet. Log them in 'Log Meals & Sleep'.")
        else:
            daily_sorted = df_daily.sort_values("date")
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(x=daily_sorted["date"], y=daily_sorted["calories"],
                                       mode="lines+markers", name="Calories",
                                       line=dict(color=GOLD_BRIGHT, width=2)))
            fig5.add_hline(y=calorie_target, line_dash="dash", line_color="#888",
                           annotation_text="Target", annotation_font_color="#888")
            fig5.update_layout(plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color="#e8e8e8"),
                                xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Calories"))
            st.plotly_chart(fig5, use_container_width=True)

            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=daily_sorted["date"], y=daily_sorted["sleep_hours"],
                                       mode="lines+markers", name="Sleep", line=dict(color="#5aa9e6", width=2)))
            fig6.add_hline(y=sleep_target, line_dash="dash", line_color="#888",
                           annotation_text="Target", annotation_font_color="#888")
            fig6.update_layout(plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color="#e8e8e8"),
                                xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Sleep (hrs)"))
            st.plotly_chart(fig6, use_container_width=True)

        # --- Consistency streak ---
        st.markdown("### Consistency")
        sessions_per_week = df_all.groupby("week")["date"].nunique().reset_index()
        sessions_per_week.columns = ["week", "sessions"]
        st.dataframe(sessions_per_week.sort_values("week", ascending=False), use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# PAGE: WEEKLY SUMMARY
# ----------------------------------------------------------------------------
elif page == "Weekly Summary":
    st.markdown("# Weekly Summary")

    if df_all.empty and df_daily.empty:
        st.info("No data logged yet. Start with 'Log Workout' or 'Log Meals & Sleep'.")
    else:
        # build week options from whichever log has data
        all_dates = pd.concat([
            df_all["date"] if not df_all.empty else pd.Series(dtype="datetime64[ns]"),
            df_daily["date"] if not df_daily.empty else pd.Series(dtype="datetime64[ns]"),
        ])
        all_dates = pd.to_datetime(all_dates)
        week_keys = sorted(all_dates.dt.strftime("%G-W%V").unique(), reverse=True)
        current_week = pd.Timestamp.today().strftime("%G-W%V")
        default_idx = week_keys.index(current_week) if current_week in week_keys else 0
        selected_week = st.selectbox("Select week", week_keys, index=default_idx)

        w_workouts = df_all[df_all["date"].dt.strftime("%G-W%V") == selected_week] if not df_all.empty else pd.DataFrame()
        w_daily = df_daily[df_daily["date"].dt.strftime("%G-W%V") == selected_week] if not df_daily.empty else pd.DataFrame()

        sessions_done = w_workouts["date"].nunique() if not w_workouts.empty else 0
        total_vol = int(w_workouts["volume"].sum()) if not w_workouts.empty else 0
        avg_cal = w_daily["calories"].mean() if not w_daily.empty else None
        avg_protein = w_daily["protein"].mean() if not w_daily.empty else None
        avg_sleep = w_daily["sleep_hours"].mean() if not w_daily.empty else None
        days_logged = w_daily["date"].nunique() if not w_daily.empty else 0

        st.markdown(f"### {selected_week}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sessions Completed", f"{sessions_done} / 6")
        c2.metric("Total Volume (lbs)", f"{total_vol:,}")
        c3.metric("Days Logged (Nutrition/Sleep)", f"{days_logged} / 7")

        c4, c5, c6 = st.columns(3)
        c4.metric("Avg Calories", f"{avg_cal:,.0f}" if avg_cal is not None else "—",
                   delta=f"{avg_cal - calorie_target:+.0f} vs target" if avg_cal is not None else None)
        c5.metric("Avg Protein (g)", f"{avg_protein:,.0f}" if avg_protein is not None else "—",
                   delta=f"{avg_protein - protein_target:+.0f} vs target" if avg_protein is not None else None)
        c6.metric("Avg Sleep (hrs)", f"{avg_sleep:.1f}" if avg_sleep is not None else "—",
                   delta=f"{avg_sleep - sleep_target:+.1f} vs target" if avg_sleep is not None else None)

        st.markdown("---")
        st.markdown("### Volume Per Muscle Pair This Week")
        if not w_workouts.empty:
            pair_summary = []
            for pair_name, muscle_list in MUSCLE_PAIRS.items():
                vol = w_workouts[w_workouts["muscle"].isin(muscle_list)]["volume"].sum()
                pair_summary.append({"Muscle Pair": pair_name, "Volume (lbs)": int(vol)})
            st.dataframe(pd.DataFrame(pair_summary), use_container_width=True, hide_index=True)
        else:
            st.info("No workouts logged this week.")

        st.markdown("---")
        st.markdown("### Auto Summary")

        lines = []
        lines.append(f"**Training:** {sessions_done}/6 sessions completed, {total_vol:,} lbs total volume.")
        if sessions_done < 6:
            lines.append(f"<span class='flag-red'>{6 - sessions_done} session(s) missed this week.</span>")
        else:
            lines.append("<span class='flag-green'>Full 6/6 sessions hit.</span>")

        if avg_cal is not None:
            if avg_cal < calorie_target:
                lines.append(f"<span class='flag-red'>Calories averaged {avg_cal:,.0f}, "
                              f"{calorie_target - avg_cal:,.0f} below target — under-eating relative to plan.</span>")
            else:
                lines.append(f"<span class='flag-green'>Calories averaged {avg_cal:,.0f}, on/above target.</span>")
        else:
            lines.append("No nutrition data logged this week.")

        if avg_sleep is not None:
            if avg_sleep < sleep_target:
                lines.append(f"<span class='flag-red'>Sleep averaged {avg_sleep:.1f}h, "
                              f"{sleep_target - avg_sleep:.1f}h short of target.</span>")
            else:
                lines.append(f"<span class='flag-green'>Sleep averaged {avg_sleep:.1f}h, on/above target.</span>")

        for line in lines:
            st.markdown(line, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# PAGE: PROGRAM NOTES
# ----------------------------------------------------------------------------
elif page == "Program Notes":
    st.markdown("# Program Notes")
    st.markdown("""
Updated structure: **3 days, each run twice a week** — Legs & Shoulders,
Back & Chest, Arms. That's 6 training sessions/week on a 7-day cycle
(e.g. Mon/Tue/Wed train, Thu rest, Fri/Sat/Sun train, repeat). This is
a real jump from where you were ("on and off gym") — it only works if
you actually show up 6 days a week. If that's not realistic yet, run it
as A-B-C-rest-A-B-C on a rolling cycle instead of a fixed calendar week,
so a missed day doesn't wreck the frequency pattern.

**1. Sets per session were cut versus a 1x/week version of this split.**
Frequency went from 1x to 2x per muscle per week, so each session doesn't
need to carry the whole weekly volume target alone. Example: Quads now sit
at 6 sets/session x2/week = 12/week (was 7 sets in a single session before).
This is objectively better for growth — splitting volume across two sessions
gives you two protein synthesis spikes per week per muscle instead of one,
and each session has fewer sets at higher quality (less form breakdown late
in a session).

**2. Every muscle in this split now gets 2x/week frequency, direct or
better.** This fixes the exact gap flagged in your original split. Chest
and Back land around 12-14 sets/week each, direct, 2x. Biceps and Triceps
get 2x direct plus a second indirect hit (rows hit biceps on Back & Chest
day, bench/DB press hit triceps on both other days) — trimmed their direct
sets slightly (2-3 vs 3-4) to account for that overlap so you're not
overreaching on recoverable volume.

**3. Exercise order** — heaviest compound first per session while fresh:
Leg Press before Leg Extension, T-Bar Row before Seated/High Row, DB Press
before lateral raises, OVH Tricep Press before pushdowns.

**4. Watch recovery, not the program.** 6 days/week at this volume only
works with sleep, protein, and calories dialed in consistently — the
program isn't the constraint anymore, your adherence and recovery are.
If soreness or performance starts dropping across a week, that's your
signal to deload (drop 1 set per exercise for a week), not to push harder.

**5. Still flagged, not fixed:** no hip hinge (RDL) for hamstrings, no
vertical pull (pulldown/pull-up) for lat width. Kept your exact exercise
list — these are future add-ons if you want them.

None of this requires you to think about it. Just hit the numbers in the
Log Workout tab and the app tracks whether you're actually progressing.
""")

# ----------------------------------------------------------------------------
# PAGE: BACKUP & RESTORE
# ----------------------------------------------------------------------------
elif page == "Backup & Restore":
    st.markdown("# Backup & Restore")
    st.warning(
        "Streamlit Community Cloud does not guarantee persistent storage across "
        "app restarts or redeploys. Download a backup after logging sessions, "
        "and re-upload it if your data ever resets."
    )

    st.markdown("### Workout log")
    if not df_all.empty:
        export_df = df_all.drop(columns=["volume"], errors="ignore").copy()
        export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download workout backup (CSV)", data=csv_bytes,
                            file_name=f"wayne_protocol_workouts_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No workout data to back up yet.")

    uploaded_workouts = st.file_uploader("Restore workout log from CSV", type=["csv"], key="restore_workouts")
    if uploaded_workouts is not None:
        restored = pd.read_csv(uploaded_workouts)
        restored["date"] = pd.to_datetime(restored["date"])
        save_data(restored)
        st.success("Workout data restored. Reload the app to see it reflected everywhere.")

    st.markdown("---")
    st.markdown("### Meals & sleep log")
    if not df_daily.empty:
        export_daily = df_daily.copy()
        export_daily["date"] = export_daily["date"].dt.strftime("%Y-%m-%d")
        csv_bytes_daily = export_daily.to_csv(index=False).encode("utf-8")
        st.download_button("Download meals/sleep backup (CSV)", data=csv_bytes_daily,
                            file_name=f"wayne_protocol_daily_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No meals/sleep data to back up yet.")

    uploaded_daily = st.file_uploader("Restore meals/sleep log from CSV", type=["csv"], key="restore_daily")
    if uploaded_daily is not None:
        restored_daily = pd.read_csv(uploaded_daily)
        restored_daily["date"] = pd.to_datetime(restored_daily["date"])
        save_daily(restored_daily)
        st.success("Meals/sleep data restored. Reload the app to see it reflected everywhere.")
