import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()
API_KEY = os.getenv("STEAM_API_KEY")

# --- Steam API Functions ---
@st.cache_data
def get_owned_games(api_key, steam_id):
    """Fetches a user's owned games from their Steam ID."""
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": True,
        "format": "json"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json().get("response", {})
        if "games" in data:
            games_list = data["games"]
            # Convert to DataFrame
            df = pd.DataFrame(games_list)
            # Process DataFrame to be more user-friendly
            df = df[['name', 'playtime_forever']].copy()
            df.rename(columns={'name': 'Game', 'playtime_forever': 'Playtime (hours)'}, inplace=True)
            df['Playtime (hours)'] = (df['Playtime (hours)'] / 60).round(1)
            df['Select'] = False
            # Reorder columns for the UI
            df = df[['Select', 'Game', 'Playtime (hours)']]
            return df.sort_values(by='Playtime (hours)', ascending=False)
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching game library: {e}")
    return pd.DataFrame() # Return an empty DataFrame on error

# --- Streamlit App Layout ---

# Basic Steam-like color profile and page configuration
st.set_page_config(
    page_title="Steam Game Recommender",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS to mimic Steam's UI
st.markdown("""
<style>
    .stApp {
        background-color: #1b2838;
        color: #c7d5e0;
    }
    .stTextInput > div > div > input {
        background-color: #3a4a5a;
        color: #c7d5e0;
    }
    .stButton > button {
        background-color: #66c0f4;
        color: #1b2838;
        font-weight: bold;
    }
    .stDataFrame {
        background-color: #2a3a4a;
        color: #c7d5e0;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #66c0f4;
    }
</style>
""", unsafe_allow_html=True)

st.title("Steam Game Recommendation Engine")

# --- API Key Check ---
if not API_KEY:
    st.error("Steam API Key not found.")
    st.info(
        "To use this app, please create a `.env` file in the project's root directory "
        "and add your Steam API key like this:\n"
        "STEAM_API_KEY='YOUR_API_KEY_HERE'"
    )
    st.stop()

# --- User Input in Sidebar ---
st.sidebar.header("User Information")
steam_id = st.sidebar.text_input(
    "Enter Your 64-bit Steam ID",
    help="You can find your Steam ID in your profile URL or using online tools."
)

if steam_id:
    games_df = get_owned_games(API_KEY, steam_id)

    if not games_df.empty:
        # --- Game Library and Recommendations in Main Area ---
        col1, col2 = st.columns(2)

        with col1:
            st.header("Your Game Library")
            st.info("Select games and adjust their playtimes to tailor your recommendations.")

            search_query = st.text_input("Search your library", "", placeholder="Filter by game name...")

            if search_query:
                display_df = games_df[games_df["Game"].str.contains(search_query, case=False, na=False)]
            else:
                display_df = games_df

            edited_df = st.data_editor(
                display_df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", default=False),
                    "Playtime (hours)": st.column_config.NumberColumn(
                        "Playtime (hours)",
                        min_value=0,
                        format="%.1f h",
                    )
                },
                disabled=["Game"],
                hide_index=True,
                height=600
            )
            selected_games = edited_df[edited_df['Select']]

        with col2:
            st.header("Your Recommendations")
            if not selected_games.empty:
                st.write("Based on your selection:")
                st.dataframe(selected_games[['Game', 'Playtime (hours)']], hide_index=True)

                # --- Recommendation Model Placeholder ---
                # In a real application, the 'selected_games' DataFrame would be passed to your model.
                st.write("### Recommended For You:")
                recommended_games = {
                    'Game': ['Divinity: Original Sin 2', 'Mass Effect Legendary Edition', 'Elden Ring'],
                    'Reason': ['Similar RPG mechanics', 'Great story-driven adventure', 'Challenging open-world combat']
                }
                rec_df = pd.DataFrame(recommended_games)
                st.table(rec_df)
            else:
                st.info("Select one or more games from your library to see recommendations.")
    else:
        st.error("Could not retrieve your game library.")
        st.info("Please check that your Steam ID is correct and that your 'Game Details' are set to 'Public' in your Steam profile's privacy settings.")
else:
    st.info("Enter your Steam ID in the sidebar to get started.")
