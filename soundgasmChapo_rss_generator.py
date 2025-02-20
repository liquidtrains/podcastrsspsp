import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime

# Configuration
SOUNDGASM_PROFILE_URL = "https://soundgasm.net/u/ClassWarAndPuppies"
RSS_FILENAME = "blackwolffeed.xml"
GITHUB_USERNAME = "liquidtrains"
REPO_NAME = "podcastrsspsp"

def get_episodes():
    response = requests.get(SOUNDGASM_PROFILE_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    episodes = []

    # Find all episode links
    for episode_div in soup.find_all("div", class_="sound-details"):
        title = episode_div.find("a").text.strip()
        episode_url = episode_div.find("a")["href"]
        date_str = episode_div.find("time").text.strip()
        
        # Extract direct audio URL
        episode_page = requests.get(f"https://soundgasm.net{episode_url}")
        episode_soup = BeautifulSoup(episode_page.text, "html.parser")
        audio_url = episode_soup.find("audio")["src"]

        # Parse date (example: "April 15, 2024")
        pub_date = datetime.strptime(date_str, "%B %d, %Y").strftime("%a, %d %b %Y %H:%M:%S GMT")

        episodes.append({
            "title": title,
            "url": audio_url,
            "pub_date": pub_date,
            "description": f"Episode: {title}"
        })

    return episodes

def generate_rss(episodes):
    fg = FeedGenerator()
    fg.title("Class War and Puppies")
    fg.link(href=SOUNDGASM_PROFILE_URL)
    fg.description("A podcast about class warfare and puppies.")
    fg.language("en-us")

    for episode in episodes:
        fe = fg.add_entry()
        fe.title(episode["title"])
        fe.link(href=episode["url"])
        fe.description(episode["description"])
        fe.pubDate(episode["pub_date"])
        fe.enclosure(episode["url"], str(len(requests.get(episode["url"]).content)), "audio/mp4")

    fg.rss_file(RSS_FILENAME)

if __name__ == "__main__":
    episodes = get_episodes()
    generate_rss(episodes)
    print(f"RSS feed generated: {RSS_FILENAME}")