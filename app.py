from collections import Counter
import pandas as pd
import requests
import streamlit as st

# --- CONFIGURATION & CLOUD STORAGE KEYS ---
JSONBIN_BIN_ID = "6a8881c4f5f4af5e29320a55"
JSONBIN_API_KEY = "$2a$10$cjEeWcU3p/jPHOTuJo1dO.zz7oLtW2z3giakq1TsdCNqgF8bqat.W"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_TEAMS_PER_DAY = 5

TEAMS = [
    "Team Ampersand",
    "Team Yottabyte",
    "Team Marvel",
    "Team Fortress",
    "Team Path Finder",
    "Team Asgard",
    "Team Clustering",
    "Team PSTT/Tools",
    "Team DevX",
    "Escalations Team",
]

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Office Day Planner", page_icon="🏢", layout="wide"
)

st.markdown(
    """
    <style>
    /* Hide bottom-right Streamlit Cloud profile badge & footer */
    footer {visibility: hidden;}
    [data-testid="stStatusWidget"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    </style>
""",
    unsafe_allow_html=True,
)

def load_data():
  headers = {"X-Master-Key": JSONBIN_API_KEY}
  try:
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    res = requests.get(url, headers=headers)
    return res.json()["record"]
  except Exception:
    return {"votes": {}}


def save_data(data):
  headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
  try:
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    requests.put(url, headers=headers, json=data)
  except Exception as e:
    st.error(f"Error saving cloud data: {e}")


data = load_data()

st.title("🏢 Office Day Voting & Schedule Coordinator")

tab1, tab2 = st.tabs(["🗳️ Vote & Rank Days", "📊 Live Schedule & Results"])

# ---------------------------------------------------------
# TAB 1: RANKED CHOICE VOTING
# ---------------------------------------------------------
with tab1:
  st.subheader("Submit or Update Your Ranked Preferences")
  st.caption(
      "Enter your name, pick your team, and rank your top 3 preferred in-office"
      " days."
  )

  col_name, col_team = st.columns(2)
  with col_name:
    raw_name = st.text_input("Enter your Full Name:")
    user_name = raw_name.strip()

  existing_vote = data["votes"].get(user_name, {}) if user_name else {}
  existing_team = existing_vote.get("team", TEAMS[0])
  existing_ranked_days = existing_vote.get(
      "ranked_days", ["Tuesday", "Wednesday", "Thursday"]
  )

  with col_team:
    team_index = TEAMS.index(existing_team) if existing_team in TEAMS else 0
    selected_team = st.selectbox("Select your Team:", TEAMS, index=team_index)

  if user_name and existing_vote:
    st.info(
        f"Existing record found for **{user_name}** ({existing_team})."
        " Resubmitting will update your choices."
    )

  st.markdown("---")
  st.markdown("### Rank Your Top 3 Preferred Days")

  d1_idx = (
      DAYS.index(existing_ranked_days[0])
      if len(existing_ranked_days) > 0 and existing_ranked_days[0] in DAYS
      else 1
  )
  d2_idx = (
      DAYS.index(existing_ranked_days[1])
      if len(existing_ranked_days) > 1 and existing_ranked_days[1] in DAYS
      else 2
  )
  d3_idx = (
      DAYS.index(existing_ranked_days[2])
      if len(existing_ranked_days) > 2 and existing_ranked_days[2] in DAYS
      else 3
  )

  c1, c2, c3 = st.columns(3)
  with c1:
    day1 = st.selectbox("🥇 1st Choice (3 pts):", DAYS, index=d1_idx)
  with c2:
    day2 = st.selectbox("🥈 2nd Choice (2 pts):", DAYS, index=d2_idx)
  with c3:
    day3 = st.selectbox("🥉 3rd Choice (1 pt):", DAYS, index=d3_idx)

  user_ranked_days = [day1, day2, day3]

  if st.button("Submit / Update Vote", type="primary"):
    if not user_name:
      st.error("Error: Please enter your name.")
    elif len(set(user_ranked_days)) < 3:
      st.error("Error: You must select 3 unique days.")
    else:
      data["votes"][user_name] = {
          "team": selected_team,
          "ranked_days": user_ranked_days,
      }
      save_data(data)
      st.success(
          f"Vote updated for {user_name}! 1st: {day1}, 2nd: {day2}, 3rd: {day3}"
      )
      st.rerun()

# ---------------------------------------------------------
# TAB 2: WEIGHTED SCHEDULING ALGORITHM
# ---------------------------------------------------------
with tab2:
  st.subheader("Optimized Team Schedule")

  if not data["votes"]:
    st.info("No votes recorded yet.")
  else:
    # 1. Calculate Weighted Team Consensus Score per Day
    # 1st Choice = 3 points, 2nd Choice = 2 points, 3rd Choice = 1 point
    WEIGHTS = {0: 3, 1: 2, 2: 1}
    team_day_scores = {team: Counter() for team in TEAMS}

    for user, vote_info in data["votes"].items():
      team = vote_info.get("team")
      ranked_days = vote_info.get(
          "ranked_days", vote_info.get("days", [])
      )  # backwards compatible
      if team in team_day_scores:
        for idx, day in enumerate(ranked_days):
          points = WEIGHTS.get(idx, 1)
          team_day_scores[team][day] += points

    # 2. Sort days per team by weighted consensus
    team_preferences = {}
    for team in TEAMS:
      scores = team_day_scores[team]
      sorted_days = [
          day
          for day, _ in sorted(
              scores.items(), key=lambda item: item[1], reverse=True
          )
      ]
      if len(sorted_days) < 5:
        sorted_days += [d for d in DAYS if d not in sorted_days]
      team_preferences[team] = sorted_days

    # 3. Schedule Assignment Engine (Assign 2 days per team, Max 5 teams/day)
    final_schedule = {day: [] for day in DAYS}
    team_assigned_days = {team: [] for team in TEAMS}

    # Pass 1: Attempt top 2 preferred days per team
    for team in TEAMS:
      for day in team_preferences[team][:2]:
        if len(final_schedule[day]) < MAX_TEAMS_PER_DAY:
          final_schedule[day].append(team)
          team_assigned_days[team].append(day)

    # Pass 2: Overflow handling for constrained days
    for team, assigned in team_assigned_days.items():
      while len(assigned) < 2:
        for day in team_preferences[team][2:] + DAYS:
          if day not in assigned and len(final_schedule[day]) < MAX_TEAMS_PER_DAY:
            final_schedule[day].append(team)
            assigned.append(day)
            break

    # 4. Render Final Schedule Matrix
    grid_data = {}
    for day in DAYS:
      grid_data[day] = [
          "✅ In Office" if team in final_schedule[day] else "🏠 Remote"
          for team in TEAMS
      ]

    df_schedule = pd.DataFrame(grid_data, index=TEAMS)
    st.dataframe(df_schedule, use_container_width=True)

    st.markdown("### 📈 Daily Capacity Utilization")
    cap_cols = st.columns(5)
    for idx, day in enumerate(DAYS):
      count = len(final_schedule[day])
      with cap_cols[idx]:
        st.metric(
            label=day,
            value=f"{count} / {MAX_TEAMS_PER_DAY} Teams",
            delta="At Capacity" if count == MAX_TEAMS_PER_DAY else "Available",
            delta_color="off" if count < MAX_TEAMS_PER_DAY else "normal",
        )

    with st.expander("View Submitted Votes & Points"):
      summary_data = [
          {
              "Name": name,
              "Team": info.get("team"),
              "1st Choice": (
                  info.get("ranked_days", ["-"] * 3)[0]
                  if len(info.get("ranked_days", [])) > 0
                  else "-"
              ),
              "2nd Choice": (
                  info.get("ranked_days", ["-"] * 3)[1]
                  if len(info.get("ranked_days", [])) > 1
                  else "-"
              ),
              "3rd Choice": (
                  info.get("ranked_days", ["-"] * 3)[2]
                  if len(info.get("ranked_days", [])) > 2
                  else "-"
              ),
          }
          for name, info in data["votes"].items()
      ]
      st.dataframe(pd.DataFrame(summary_data), use_container_width=True)