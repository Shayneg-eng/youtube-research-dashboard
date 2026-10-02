import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import json
from urllib.parse import urlparse, parse_qs

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load OpenAI/Poe client
try:
    import openai
except ImportError:
    openai = None

POE_API_KEY = os.getenv('POE_API_KEY')
TRANSCRIPT_API_KEY = os.getenv('TRANSCRIPT_API_KEY')

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    parsed = urlparse(url)
    
    # Extract video ID from query parameters
    if 'youtube.com' in parsed.netloc:
        query_params = parse_qs(parsed.query)
        video_id = query_params.get('v', [None])[0]
        if video_id:
            # Clean any additional parameters from video ID
            video_id = video_id.split('&')[0].split('?')[0]
            return video_id
    
    # If already a youtu.be URL
    elif 'youtu.be' in parsed.netloc:
        video_id = parsed.path.strip('/')
        # Clean any additional parameters from video ID
        video_id = video_id.split('?')[0].split('&')[0]
        return video_id
    
    return None

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================
MAX_VIDEOS = 30  # Maximum number of videos to include in output
DAYS_BACK = 1  # Number of days to look back for recent videos
FETCH_SUMMARIES = True  # Whether to fetch summaries using Poe API
SUMMARY_DELAY = 1  # Delay between summary API calls (seconds)

# Channel IDs mapping
CHANNEL_IDS = {
    "NGO Monitor": "UCaPy5NRrqNLZHZ7BGlMmn7g",
    "The Free Press": "UCSRRURbKlPf1HwPUhjmufTg",
    "InfluenceWatch": "UCp7NBbx93BDRMe2jM2h-Wpw",
    "Seamus Bruner": "UC4vj-WN8MqkItkewh1TGyMA",
    "Ami Horowitz": "UCLjcPQo6Tn1Iwfdr8X7S2CA",
    "Julio Rosas": "UC9Zv3mV8R_KL5LmePl_AXXg",
    "Andy Ngo": "UCmmfVSRVwMSfHdRf6v3lPxQ",
    "Savannah Hernandez": "UCjP7obypR9QbDb9YM_VaJoQ",
    "David Bedein": "UCuxgEyMeaks7HS5gAw6Tt7w",
    "HonestReporting": "UCxb2M5GmklFJxkRbH3pGM4Q",
    "Palestinian Media Watch": "UCMsgtVuEB3figdSPz_9dRIA",
    "CAMERA": "UC0C-w0YjGpqDXGB8IHb662A",
    "Middle East Forum": "UCc9cGV0srJhwKSSxBwLMi5A",
    "Breitbart News": "UCmgnsaQIK1IR808Ebde-ssA",
    "Rebel News": "UCGy6uV7yqGWDeUWTZzT3ZEg",
    "Drew Hernandez": "UCMaLetBcZ8fqsoIryB015og",
    "Campus Reform": "UCA8sK_Bba0Eb-k33bD0ldhw",
    "Fleccas Talks": "UCIpwPuJsrboNnf200oV8cWQ",
    "Mark Dice": "UCzUV5283-l5c0oKRtyenj6Q",
    "Lauren Chen": "UCfXIeNDtl1wvsAag4KaFlCw",
    "Slightly Offens*ve": "UCMRxoFJPZiBcxgFzxN0ao-w",
    "Tyler Oliveira": "UCY8SLLJjWpS4sx1dEqECaIw",
    "Channel 5 with Andrew Callaghan": "UC-AQKm7HUNMmxjdS371MSwg",
    "All Gas No Brakes": "UCtqxG9IrHFU_ID1khGvx9sA",
}

def check_channel_rss(channel_name, channel_id, days=1):
    """Check channel RSS feed for recent videos"""
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        response = requests.get(rss_url, timeout=10)
        
        if response.status_code != 200:
            return None
        
        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days)
        recent_videos = []
        
        for entry in root.findall('atom:entry', namespace):
            published_str = entry.find('atom:published', namespace).text
            published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            
            if published > cutoff_date:
                title = entry.find('atom:title', namespace).text
                video_id = entry.find('atom:id', namespace).text.split(':')[-1]
                
                recent_videos.append({
                    'title': title,
                    'published': published.isoformat(),
                    'published_str': published.strftime('%Y-%m-%d %H:%M'),
                    'videoId': video_id
                })
        
        if recent_videos:
            return {
                'channel': channel_name,
                'channel_url': f"https://youtube.com/channel/{channel_id}",
                'videos': recent_videos
            }
        
        return None
        
    except Exception as e:
        return None

def get_video_transcript(video_title, video_url, channel_name):
    """Fetch full transcript from YouTube video with retry logic"""
    if not TRANSCRIPT_API_KEY:
        return None
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            return None
        
        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Fetch transcript from API
                transcript_response = requests.post(
                    "https://www.youtube-transcript.io/api/transcripts",
                    headers={
                        "Authorization": f"Basic {TRANSCRIPT_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={"ids": [video_id]},
                    timeout=30
                )
                
                # Handle rate limiting with exponential backoff
                if transcript_response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        return None
                
                if transcript_response.status_code != 200:
                    return None
                
                data = transcript_response.json()
                
                # Extract transcript text using correct API structure
                if not data or len(data) == 0:
                    return None
                
                if 'tracks' not in data[0] or len(data[0]['tracks']) == 0:
                    return None
                
                if 'transcript' not in data[0]['tracks'][0]:
                    return None
                
                # Extract just the text, ignoring timestamps
                transcript_text = " ".join([segment["text"] for segment in data[0]["tracks"][0]["transcript"]])
                
                if not transcript_text.strip():
                    return None
                
                return transcript_text
                
            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    return None
        
    except Exception:
        return None

def generate_daily_report(all_videos):
    """Generate a comprehensive daily report from all video transcripts using Claude"""
    if not POE_API_KEY or not openai:
        return None
    
    try:
        client = openai.OpenAI(
            api_key=POE_API_KEY,
            base_url="https://api.poe.com/v1",
        )
        
        # Build detailed transcripts list for report
        transcripts_list = "\n\n".join([
            f"**{video['channel']}** - {video['title']}\nTranscript: {video.get('transcript', 'No transcript available')[:3000]}..."
            for video in all_videos
            if video.get('transcript')
        ])
        
        if not transcripts_list:
            return None
        
        prompt = f"""You are a news analyst helping Nate Friedman stay informed. Nate's work focuses on:
- On-the-street interviews and field reporting
- Tracking money flow and funding (NGOs, protests, organizations)
- Documenting protests and activism
- Exposing connections between organizations and movements
- Investigative journalism on funding and organization tactics
- Ground truth reporting

Based on these YouTube video transcripts from today, write a focused daily report that ONLY covers noteworthy creators doing work in Nate's sphere. Ignore creators not doing this type of work.

Focus on:
1. STREET REPORTING: Who is doing on-the-street interviews, confrontations, or field documentation
2. MONEY TRACKING: Who is investigating funding, money flow, or organizational financing
3. PROTEST DOCUMENTATION: Who is documenting protests, activism, or organizing efforts
4. INVESTIGATIONS: Who is doing investigative work on organizations, connections, or tactics
5. SPECIFIC FINDINGS: What concrete information or evidence has been uncovered
6. NOTABLE OPERATIONS: What specific work is being done and by whom

Only mention creators doing this type of substantive investigative or field work. Skip entertainment, general commentary, or lifestyle content unless directly relevant to tracking money/protests/organization.

VIDEO TRANSCRIPTS FROM TODAY:
{transcripts_list}

Generate a focused report (250-400 words) covering only the noteworthy investigative/field work relevant to Nate's sphere."""
        
        chat = client.chat.completions.create(
            model="claude-haiku-4.5",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        report = chat.choices[0].message.content
        return report
        
    except Exception as e:
        return None

def filter_relevant_videos(all_videos, max_count):
    """Use Claude to filter videos relevant to Nate Friedman's interests"""
    if not POE_API_KEY or not openai or len(all_videos) <= max_count:
        return list(range(min(max_count, len(all_videos))))
    
    try:
        client = openai.OpenAI(
            api_key=POE_API_KEY,
            base_url="https://api.poe.com/v1",
        )
        
        video_list = "\n".join([
            f"{i+1}. [{video['channel']}] {video['title']}"
            for i, video in enumerate(all_videos)
        ])
        
        prompt = f"""You are helping curate content for Nate Friedman, who focuses on INVESTIGATIVE AND FIELD WORK:
- Street interviews and confrontations with key figures
- Documentation of funding flows and money trails (NGOs, political organizations, protest funding)
- Protest and activist documentation (who organized, how funded, what goals)
- Exposing organizational connections and tactics
- Specific investigations by individual reporters (not commentary)
- Ground truth reporting from the field

PRIORITY: Select videos that represent DIVERSE INVESTIGATIVE WORK from INDIVIDUAL REPORTERS/CREATORS.

For example:
- Reporter A: Tracking fraud-to-funding pipelines with documentation
- Reporter B: On-the-street interviews with activist organizers
- Reporter C: Protest funding paper trail investigation
- Reporter D: NGO operational tactics documentation

You MUST select exactly {max_count} videos that:
1. Feature individual reporters/creators doing SPECIFIC work (not general commentary)
2. Represent diverse investigation types (street work, funding, protests, connections, etc.)
3. Show what SPECIFIC actions or investigations each creator is pursuing
4. Would be actionable intelligence for tracking who's doing what in Nate's sphere

Ignore: General political commentary, entertainment, lifestyle, generic news coverage, celebrity content

VIDEO LIST:
{video_list}

Reply with ONLY the numbers of exactly {max_count} videos, separated by commas. For example: 1,3,5,7,9

Do not include any other text or explanation. You must return exactly {max_count} numbers."""
        
        chat = client.chat.completions.create(
            model="claude-haiku-4.5",
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = chat.choices[0].message.content.strip()
        selected_indices = [int(x.strip()) - 1 for x in response.split(',')]
        return selected_indices[:max_count]
        
    except Exception as e:
        return list(range(min(max_count, len(all_videos))))

def main():
    results = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_channel = {
            executor.submit(check_channel_rss, name, cid, days=DAYS_BACK): name 
            for name, cid in CHANNEL_IDS.items()
        }
        
        for future in as_completed(future_to_channel):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except:
                pass
    
    if not results:
        return {"videos": [], "report": None, "generated": datetime.now().isoformat()}
    
    all_videos = []
    for result in results:
        for video in result['videos']:
            all_videos.append({
                'channel': result['channel'],
                'channel_url': result['channel_url'],
                'title': video['title'],
                'published': video['published'],
                'published_str': video['published_str'],
                'videoId': video['videoId'],
                'url': f"https://youtube.com/watch?v={video['videoId']}"
            })
    
    all_videos.sort(key=lambda x: x['published'], reverse=True)
    
    # Filter videos
    if len(all_videos) > MAX_VIDEOS:
        selected_indices = filter_relevant_videos(all_videos, MAX_VIDEOS)
        selected_videos = [all_videos[i] for i in selected_indices if i < len(all_videos)]
        all_videos = selected_videos
    
    # Fetch transcripts sequentially with rate limiting
    successful_transcripts = 0
    if FETCH_SUMMARIES and POE_API_KEY and openai:
        for i, video in enumerate(all_videos):
            try:
                transcript = get_video_transcript(video['title'], video['url'], video['channel'])
                if transcript:
                    video['transcript'] = transcript
                    successful_transcripts += 1
                else:
                    video['transcript'] = None
                
                # Add delay between requests (except for last item)
                if i < len(all_videos) - 1:
                    time.sleep(1.5)
                    
            except:
                video['transcript'] = None
    else:
        for video in all_videos:
            video['transcript'] = None
    
    # Generate daily report
    daily_report = None
    if successful_transcripts > 0:
        daily_report = generate_daily_report(all_videos)
    
    return {
        "videos": all_videos,
        "report": daily_report,
        "generated": datetime.now().isoformat(),
        "total_channels": len(CHANNEL_IDS),
        "channels_with_videos": len(results),
        "days_back": DAYS_BACK,
        "transcripts_fetched": successful_transcripts
    }

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
