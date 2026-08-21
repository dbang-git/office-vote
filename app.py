from collections import Counter
import pandas as pd
import requests
import streamlit as st

# --- CLOUD STORAGE CONFIGURATION ---
# Replace these strings with your actual keys from JSONBin.io
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
]


def load_data():
  headers = {"X-Master-Key": JSONBIN_API_KEY}
  try:
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    res = requests.get(url, headers=headers)
    return res.json()["record"]
  except Exception as e:
    st.error(f"Error loading cloud data: {e}")
    return {"votes": {}}


def save_data(data):
  headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
  try:
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    requests.put(url, headers=headers, json=data)
  except Exception as e:
    st.error(f"Error saving cloud data: {e}")


data = load_data()

st.set_page_config(
    page_title="Office Day Planner", page_icon="🏢", layout="wide"
)
st.title("🏢 Office Day Voting & Schedule Coordinator")

tab1, tab2 = st.tabs(["🗳️ Vote Preferred Days", "📊 Live Schedule & Results"])

# ---------------------------------------------------------
# TAB 1: USER VOTING & MODIFICATION
# ---------------------------------------------------------
with tab1:
  st.subheader("Submit or Modify Your Preferences")
  st.caption(
      "Enter your name to register a vote or update an existing selection."
  )

  col1, col2 = st.columns(2)
  with col1:
    raw_name = st.text_input("Enter your Full Name:")
    user_name = raw_name.strip()

  existing_vote = data["votes"].get(user_name, {}) if user_name else {}
  existing_team = existing_vote.get("team", TEAMS[0])
  existing_days = existing_vote.get("days", [])

  with col2:
    team_index = TEAMS.index(existing_team) if existing_team in TEAMS else 0
    selected_team = st.selectbox("Select your Team:", TEAMS, index=team_index)

  if user_name and existing_vote:
    st.info(
        f"Existing vote found for **{user_name}** ({existing_team})."
        " Submitting again will update your existing preferences."
    )

  user_days = st.multiselect(
      "Select exactly 2 days:",
      DAYS,
      default=existing_days if len(existing_days) == 2 else [],
      max_selections=2,
  )

  if st.button("Submit / Update Vote", type="primary"):
    if not user_name:
      st.error("Error: Please enter your name.")
    elif len(user_days) != 2:
      st.error("Error: You must select exactly 2 days.")
    else:
      data["votes"][user_name] = {"team": selected_team, "days": user_days}
      save_data(data)
      st.success(
          f"Vote saved for {user_name} ({selected_team})! Selected:"
          f" {user_days[0]} & {user_days[1]}"
      )
      st.rerun()

# ---------------------------------------------------------
# TAB 2: AGGREGATION & SCHEDULING ALGORITHM
# ---------------------------------------------------------
with tab2:
  st.subheader("Calculated Team Schedule")

  if not data["votes"]:
    st.info("No votes have been recorded yet.")
  else:
    team_day_scores = {team: Counter() for team in TEAMS}

    for user, vote_info in data["votes"].items():
      team = vote_info.get("team")
      days = vote_info.get("days", [])
      if team in team_day_scores:
        for day in days:
          team_day_scores[team][day] += 1

    team_preferences = {}
    for team in TEAMS:
      counts = team_day_scores[team]
      sorted_days = [
          day
          for day, _ in sorted(
              counts.items(), key=lambda item: item[1], reverse=True
          )
      ]
      if len(sorted_days) < 2:
        sorted_days += [d for d in DAYS if d not in sorted_days]
      team_preferences[team] = sorted_days

    final_schedule = {day: [] for day in DAYS}
    team_assigned_days = {team: [] for team in TEAMS}

    for team in TEAMS:
      for day in team_preferences[team][:2]:
        if len(final_schedule[day]) < MAX_TEAMS_PER_DAY:
          final_schedule[day].append(team)
          team_assigned_days[team].append(day)

    for team, assigned in team_assigned_days.items():
      while len(assigned) < 2:
        for day in team_preferences[team][2:] + DAYS:
          if day not in assigned and len(final_schedule[day]) < MAX_TEAMS_PER_DAY:
            final_schedule[day].append(team)
            assigned.append(day)
            break

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

    with st.expander("View Individual Submitted Votes"):
      summary_data = [
          {
              "Name": name,
              "Team": info.get("team"),
              "Preferred Days": ", ".join(info.get("days", [])),
          }
          for name, info in data["votes"].items()
      ]
      st.dataframe(pd.DataFrame(summary_data), use_container_width=True)