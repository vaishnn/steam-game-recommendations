import requests
import time

def get_steam_games_with_good_ratings(api_key):
    """
    Fetches Steam games with more than 50 reviews and a positive rating of over 50%.

    Args:
        api_key: Your Steam Web API key.

    Returns:
        A list of dictionaries, where each dictionary contains the name of a game,
        its AppID, the total number of reviews, and the percentage of positive reviews.
    """
    all_games_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    app_details_base_url = "https://store.steampowered.com/appreviews/"

    # --- Step 1: Get the list of all apps on Steam ---
    try:
        response = requests.get(all_games_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        all_apps = response.json().get('applist', {}).get('apps', [])
        print(f"Found {len(all_apps)} total applications on Steam.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the list of all apps: {e}")
        return []

    # --- Step 2 & 3: Iterate through apps, get reviews, and filter ---
    highly_rated_games = []
    for app in all_apps:
        app_id = app.get('appid')
        app_name = app.get('name')

        if not app_id or not app_name:
            continue

        # Construct the URL for the review data for this app
        app_reviews_url = f"{app_details_base_url}{app_id}?json=1"

        try:
            # Make a request to get the review summary for the current app
            review_response = requests.get(app_reviews_url)
            review_response.raise_for_status()
            review_data = review_response.json()

            # Check if the request was successful and contains review summary data
            if review_data.get('success') == 1:
                query_summary = review_data.get('query_summary', {})
                total_reviews = query_summary.get('total_reviews', 0)

                if total_reviews > 50:
                    total_positive = query_summary.get('total_positive', 0)

                    # Calculate the positive rating percentage
                    positive_rating_percent = (total_positive / total_reviews) * 100 if total_reviews > 0 else 0

                    if positive_rating_percent > 50:
                        highly_rated_games.append({
                            'name': app_name,
                            'appid': app_id,
                            'total_reviews': total_reviews,
                            'positive_rating_percent': round(positive_rating_percent, 2)
                        })
                        print(f"Found a qualifying game: {app_name}")

            # A short delay to be respectful to the API and avoid rate limiting
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            # Some app IDs might not have review pages, so we can often ignore these errors
            # print(f"Could not fetch review data for AppID {app_id} ({app_name}): {e}")
            pass
        except Exception as e:
            print(f"An unexpected error occurred for AppID {app_id} ({app_name}): {e}")

    return highly_rated_games

if __name__ == '__main__':
    # --- IMPORTANT ---
    # Replace "YOUR_API_KEY" with the actual API key you obtained from Steam.
    my_api_key = "7B8F07DD3555D8B8219688025F2CC972"

    if my_api_key == "YOUR_API_KEY":
        print("Please replace 'YOUR_API_KEY' with your actual Steam Web API key.")
    else:
        games = get_steam_games_with_good_ratings(my_api_key)

        if games:
            print("\n--- Highly Rated Steam Games (More than 50 reviews, >50% positive) ---")
            for game in games:
                print(
                    f"Name: {game['name']}, "
                    f"Total Reviews: {game['total_reviews']}, "
                    f"Positive Rating: {game['positive_rating_percent']}%"
                )
            print(f"\nFound a total of {len(games)} games matching the criteria.")
        else:
            print("\nCould not retrieve any games matching the criteria. Please check your API key and network connection.")
