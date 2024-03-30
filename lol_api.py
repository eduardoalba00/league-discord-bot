import os
import aiohttp
from dotenv import load_dotenv
import datetime

# Load environment variables from .env file
load_dotenv()

# Handler function for all calls made to riot api
async def handle_api_call(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                response.raise_for_status()  # Raise an exception for non-200 status codes
                data = await response.json()
                return data
            except aiohttp.ClientResponseError as e:
                print(f"Error in API call: {e.status}")
                return None

async def fetch_summoner_puuid_by_riot_id(summoner_riot_id):
    game_name, tag = summoner_riot_id.split(" #")
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag}?api_key={os.getenv("RIOT_API_KEY")}"
    data = await handle_api_call(url)
    return data["puuid"] if data is not None else None

# Fetches match data for all matches played in the last {range} days
# queue_id is set to 420 by default for ranked solo queue
async def fetch_matches_data_by_day_range(summoner_puuid, range=7, queue_id=420):
    today = datetime.datetime.today()
    start = today - datetime.timedelta(days=range)
    today_formatted = int(today.timestamp())
    start_formatted = int(start.timestamp())
    matches_data = []

    print(f"Fetching matches data for summoner with puuid {summoner_puuid} for the last {range} days")
    url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner_puuid}/ids?startTime={start_formatted}&endTime={today_formatted}&queue={queue_id}&start=0&count=100&api_key={os.getenv("RIOT_API_KEY")}"
    match_ids =  await handle_api_call(url)

    if match_ids:
        for id in match_ids:
            url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{id}?api_key={os.getenv("RIOT_API_KEY")}"
            single_match_data = await handle_api_call(url)

            if single_match_data:
                matches_data.append(single_match_data)
    
    if matches_data == []:
        print(f"No matches were found for summoner with puuid {summoner_puuid} in the last {range} days.")
        return None
    else:
        print(f"{len(matches_data)} matches were found for summoner with puuid {summoner_puuid} in the last {range} days")
        return matches_data

# Fetches stats for summoner for a given day range
async def fetch_summoner_stats_by_day_range(summoner_puuid, range=7):
    print(f"Fetching stats for summoner with puuid {summoner_puuid} for the past {range} days")

    matches_data = await fetch_matches_data_by_day_range(summoner_puuid, range)
    stats = calculate_stats(summoner_puuid, matches_data)

    print(f"Finished calculating stats for summoner with puuid {summoner_puuid} for matches played in the last {range} days")
    return stats

# calculates stats for a summoner with a given set of matches data
def calculate_stats(summoner_puuid, matches_data):
    data_keys = ['Total Matches', 'Average Assists', 'Ability Uses', 'Average Damage Per Minute', 'Average Gold Per Minute',  
                 'Average KDA', 'Average Kill Participation', 'Skillshots Hit', 'Average Solo Kills',  
                 'Average Team Damage Percentage', 'Average Damage To Champions',  'Average Enemy Missing Pings']
    # Initialize the dictionary with keys set to 0
    data = {key: 0 for key in data_keys}

    if matches_data:
        data["Total Matches"] = len(matches_data)
        for match in matches_data:
            participants = match["info"]["participants"]
            stats = next((obj for obj in participants if obj.get('puuid') == summoner_puuid), None)
            
            data["Average Assists"] += stats["assists"]
            data["Ability Uses"] += stats["challenges"]["abilityUses"]
            data["Skillshots Hit"] += stats["challenges"]["skillshotsHit"]
            data["Average Solo Kills"] += stats["challenges"]["soloKills"]
            data["Average Enemy Missing Pings"] += stats["enemyMissingPings"]
            data["Average Damage Per Minute"] += stats["challenges"]["damagePerMinute"]
            data["Average Gold Per Minute"] += stats["challenges"]["goldPerMinute"]
            data["Average KDA"]  += stats["challenges"]["kda"]
            data["Average Kill Participation"] += stats["challenges"]["killParticipation"]
            data["Average Team Damage Percentage"] += stats["challenges"]["teamDamagePercentage"]
            data["Average Damage To Champions"] += stats["totalDamageDealtToChampions"]
        
        # calculate averages
        data = {key: (value / len(matches_data) if "Average" in key else value) for key, value in data.items()}
        # Round values to 2 decimal places
        rounded_data = {key: round(value, 2) for key, value in data.items()}

        return rounded_data
    else:
        return data

