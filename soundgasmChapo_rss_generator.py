import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from email.utils import formatdate
from dateutil import parser  # Requires 'python-dateutil'
import re

# Configuration
SOUNDGASM_PROFILE_URL = "https://soundgasm.net/u/ClassWarAndPuppies"
RSS_FILENAME = "feed.xml"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
VALID_AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.ogg', '.aac'}  # Common audio formats

def get_episodes():
    try:
        response = requests.get(SOUNDGASM_PROFILE_URL, headers=HEADERS)
        response.raise_for_status()
        print(f"Profile fetched successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching profile: {str(e)}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    episodes = []

    for episode_div in soup.find_all("div", class_="sound-details"):
        title_link = episode_div.find("a", href=True)
        if not title_link:
            print("No title link found in sound-details div")
            continue

        title = title_link.text.strip()
        episode_path = title_link["href"]
        print(f"Raw href: {episode_path}")
        
        if episode_path.startswith("http"):
            episode_url = episode_path
        else:
            episode_url = f"https://soundgasm.net{episode_path}"

        # Extract date (fallback to title parsing)
        date_element = episode_div.find("span", class_="sound-date")
        if date_element:
            date_str = date_element.text.strip()
            try:
                parsed_date = parser.parse(date_str, fuzzy=True)
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                print(f"Parsed date from span: {parsed_date}")
                pub_date = formatdate(parsed_date.timestamp(), localtime=False)
            except ValueError as e:
                print(f"Invalid date '{date_str}' in span: {e}")
                pub_date = None
        else:
            print(f"No date span for {title}, attempting title parse")
            pub_date = None
            date_match = re.search(r'\[(\d{4}\.\d{2}\.\d{2})\]|\((\d{1,2}-\d{1,2}-\d{2,4})\)', title)
            if date_match:
                date_str = date_match.group(1) or date_match.group(2)
                try:
                    if date_str and '.' in date_str:
                        parsed_date = datetime.strptime(date_str, "%Y.%m.%d")
                    else:
                        parsed_date = parser.parse(date_str, dayfirst=False, yearfirst=False)
                    if parsed_date.year < 1970:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 100)
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    print(f"Parsed date from title '{date_str}': {parsed_date}")
                    pub_date = formatdate(parsed_date.timestamp(), localtime=False)
                except ValueError as e:
                    print(f"Could not parse date '{date_str}' from title: {e}")
            if not pub_date:
                print(f"Fallback to current time for {title}")
                pub_date = formatdate(localtime=False)

        # Fetch audio URL
        try:
            print(f"Fetching episode: {episode_url}")
            episode_resp = requests.get(episode_url, headers=HEADERS)
            episode_resp.raise_for_status()
            episode_soup = BeautifulSoup(episode_resp.text, "html.parser")
            # Try multiple ways to find audio URL
            audio_element = episode_soup.find("audio")
            audio_url = audio_element.get("src") if audio_element else None
            if not audio_url:
                source_element = episode_soup.find("source")
                audio_url = source_element.get("src") if source_element else None
            if not audio_url:
                # Fallback: search for audio URL in raw text
                audio_match = re.search(r'https?://[^\'"\s]+\.(?:mp3|m4a|wav|ogg|aac)', episode_resp.text)
                audio_url = audio_match.group(0) if audio_match else None
            if not audio_url:
                print(f"No audio URL found for {title}. Episode HTML:")
                print(episode_soup.prettify()[:1000])  # Limit output
                continue
            # Validate audio format
            if not any(audio_url.lower().endswith(ext) for ext in VALID_AUDIO_EXTENSIONS):
                print(f"Invalid audio format for {title}: {audio_url}")
                continue
            print(f"Found audio URL for {title}: {audio_url}")
        except Exception as e:
            print(f"Error processing {title}: {str(e)}")
            continue

        episodes.append({
            "title": title,
            "episode_url": episode_url,
            "audio_url": audio_url,
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
        fe.link(href=episode["episode_url"])
        fe.guid(episode["episode_url"], permalink=True)
        fe.description(episode["description"])
        fe.pubDate(episode["pub_date"])
        # Set MIME type based on extension
        ext = episode["audio_url"].split('.')[-1].lower()  # Fixed: use episode["audio_url"]
        mime_type = 'audio/mpeg' if ext == 'mp3' else 'audio/mp4' if ext == 'm4a' else 'audio/x-' + ext
        fe.enclosure(episode["audio_url"], "0", mime_type)

    fg.rss_file(RSS_FILENAME, pretty=True)

if __name__ == "__main__":
    episodes = get_episodes()
    if episodes:
        generate_rss(episodes)
        print(f"Success! Generated RSS feed with {len(episodes)} episodes.")
    else:
        print("No episodes found. Check the profile URL or website structure.")