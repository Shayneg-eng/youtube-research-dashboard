import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
from urllib.parse import urlparse, parse_qs

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
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

# Channel IDs mapping - PASTE YOUR CHANNEL_IDS DICTIONARY HERE
CHANNEL_IDS = {
    # Core On-Ground Street Political Journalists (Verified)
    "Nick Shirley": "UC2Uioh1tYQkNuHLSBpzdfCg",
    "Channel 5 with Andrew Callaghan": "UC-AQKm7HUNMmxjdS371MSwg",
    "All Gas No Brakes": "UCtqxG9IrHFU_ID1khGvx9sA",
    "Peter Santenello": "UC3Vuq4Q1bKFtAiKYlwRv3oA",
    "Tyler Oliveira": "UCY8SLLJjWpS4sx1dEqECaIw",
    "Brandon Buckingham": "UCketCWflVRWm3AEzbno9-_w",
    "Tommy G": "UCakIVH4t7k4vZe1AWPpewgA",
    
    # On-Ground Event/Protest Coverage (Verified)
    "Ford Fischer News2Share": "UCbBm6SZ235HFxwVKC7Po5IA",
    "Status Coup Jordan Chariton": "UC0pCsHlEEmCfxllZSlRB2Og",
    "Tayler Hansen": "UCnygMiEjtbT_nqxrxZepykw",
    "Elijah Schaffer": "UC1baPZaaCEiHcNR4U_eoMFQ",
    "Drew Hernandez": "UCMaLetBcZ8fqsoIryB015og",
    "Savannah Hernandez": "UCjP7obypR9QbDb9YM_VaJoQ",
    "Julio Rosas": "UC9Zv3mV8R_KL5LmePl_AXXg",
    "Scootercaster": "UCoi5pABIDpya7N5OdDnDScg",
    "Kalen D'Almeida": "UCr2aQnoBkgEAzCONH5ZVDiQ",
    "Andy Ngo": "UCmmfVSRVwMSfHdRf6v3lPxQ",
    
    # Israel/Palestine On-Ground Coverage
    "Corey Gil-Shuster": "UCc4iogeOUXNw1RZSNTOlMeg",
    "+972 Magazine": "UCdPB7J77CNSNWC6Qh3Ys1fg",
    "Middle East Eye": "UCR0fZh5SBxxMNYdg0VzRFkg",
    "Electronic Intifada": "UC9jY5IcAA99wX8MZQ9K9r-Q",  # From your document
    "Al Jazeera English": "UCNye-wNBqNL5ZzHSJj3l8Bg",  # From your document
    "TRT World": "UC7fWeaHhqgM4Ry-RMpM2YYw",  # From your document
    
    # International/Conflict Ground Coverage (Verified)
    "Popular Front Jake Hanrahan": "UC_2WoPonjo8MdKOF5VCpr9g",
    "Patrick Lancaster": "UCbjTWVaRx6jMN5ZYgbqe2_w",
    
    # Street Interview Political Content
    "Fleccas Talks": "UCIpwPuJsrboNnf200oV8cWQ",
    "Daniel Mac": "UCYRg9w3AfuRCKfh4JcDp8xw",
    "Dose of Society": "UCb6qEkC-Rb2yS63kFJPwUQw",
    "Great Chat": "UCHbf6040M6kl_8VncJITdNQ",
    "Simon Squibb": "UCGznz4NfW5iymkvn1l40qyA",
    "Steven Franz": "UCRj10a3GWf2bMn-zZBAeR-A",
    "Takashii from Japan": "UCPSx50w7WavmAXmYowlhNWQ",
    "Israel Padilla": "UCZeGmmXuii47U8JGFogdZBA",
    
    # Urban/Community Political Documentation
    "CharlieBo313": "UCXpkSlxIY73Wr6jbCb2eKLA",
    "Soft White Underbelly Mark Laita": "UCCvcd0FYi58LwyTQP9LITpA",
    "Invisible People": "UCh4pyZUB0mNzieaKv831flA",
    
    # International Political Street Coverage
    "Asian Boss": "UC2-_WWPT_124iN6jiym4fOw",
    "Bald and Bankrupt": "UCxDZs_ltFFvn0FDHT6kmoXA",
    "Harald Baldr": "UCKr68ZJ4vv6VloNdnS2hjhA",
    "Indigo Traveller": "UCXulruMI7BHj3kGyosNa0jA",
    "1420 Russian Street Interviews": "UCl4R4M9YVfYjjPmILU2Ie1A",
    "serpentza": "UCl7mAGnY4jh4Ps8rhhh8XZg",
    "laowhy86": "UChvithwOECK5g_19TjldMKw",
    "China Insights": "UCwjvvgGX6oby5mZ3gbDe8Ug",
    "Lei's Real Talk": "UCIRXrnX2_k7AizFQgsdcqjQ",
    
    # Field Investigative Journalism
    "James O'Keefe": "UCjl4caubo8dWBlNTaMcrVQg",
    "Project Veritas": "UCL9PlYkRD3Q-RZca6CCnPKw",
    "Luke Rudkowski We Are Change": "UChwwoeOZ3EJPobW83dgQfAg",
    
    # From Your Document - Additional Verified
    "Johnny Harris": "UCmGSJVG3mCRXVOP4yZrU1Dw",
    "Democracy Now": "UCzuqE7-t13O4NIDYJfakrhw",
    "The Grayzone": "UCEXR8pRTkE2vFeJePNe9UcQ",
    "BreakThrough News": "UCiinSjWS3E0vtAa3DCvp7iA",
    "Abby Martin": "UCG29FnXZm4F5U8xpqs1cs1Q",
    "Richard Medhurst": "UCB1u_wJThc3_e5J4VVj7hQQ",
    "Aaron Maté": "UC-OKkVxTcgGo34pWUC9CIIw",
    "Glenn Greenwald": "UChzVhAwzGR7hV-4O8ZmBLHg",
    "Chris Hedges": "UCEATT6H3U5lu20eKPuHVN8A",
    "Ben Norton": "UCwlvSJdcMc7iGdR-aducSog",
    "Max Blumenthal": "UCEXR8pRTkE2vFeJePNe9UcQ",  # Often appears with Grayzone
    "Dan Cohen": "UCoEV0G4jwhQGy87oVvTP_rw",
    "Rania Khalek": "UCiinSjWS3E0vtAa3DCvp7iA",  # Often with BreakThrough News
    "Novara Media": "UCOzMAa6IhV6uwYQATYG_2kg",
    "Double Down News": "UCeRYN0tYBQVrC2cKsxJjdow",
    "Owen Jones": "UCSYCo8uRGF39qDCxF870K5Q",
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
                    'published': published,
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
        
        prompt = f"""You are a competitive intelligence analyst for investigative street journalist Nate Friedman.

NATE'S STYLE & APPROACH:
- Non-confrontational interview technique: lets subjects speak freely, nods, listens without interrupting
- Never corrects misinformation on the spot - saves fact-checking for post-production commentary
- Focuses on exposing knowledge gaps and contradictions in protesters/activists
- Investigates funding sources and organizational networks behind protests
- Covers anti-Israel protests, voter fraud claims, political demonstrations in NYC
- Goes viral by letting people reveal their own inconsistencies naturally
- Creates short clips for social media with his fact-check commentary added after

NATE'S MAIN BEATS:
- Anti-Israel/pro-Palestine protests and their funding
- Protest organizers and their connections
- Voter fraud investigations
- Political demonstrations in NYC
- NGO/nonprofit funding of activism

Analyze these YouTube transcripts from the last 24 hours. Identify ONLY creators doing similar investigative/street work.

For each relevant creator/video, extract:

**CREATOR & VIDEO INFO:**
- Channel name (use exact name from transcript)
- Video title
- Creator's name if mentioned

**WHAT THEY COVERED:**
- Specific event/topic/investigation with location
- Key findings or claims (include 1-2 direct quotes)
- Organizations/people named in the video

**HOW THEY COVERED IT (compare to Nate's style):**
- Interview approach with specific examples from video
- Actual questions they asked (quote 2-3 verbatim if possible)
- When/how they fact-check vs. Nate's post-production method
- Notable interview moments (quote exchanges that worked/failed)

**WHAT NATE CAN LEARN:**
- Specific question techniques (quote the exact questions that got good responses)
- Moments where their approach exposed contradictions (quote the exchange)
- Tactics that fit Nate's style with examples
- Follow-up angles based on what was said

**COMPETITIVE POSITIONING:**
- How [Creator Name]'s style differs from Nate's approach
- Specific advantages Nate has (reference their weak moments)
- Topics where Nate could outperform them

**ACTIONABLE INTEL FOR NATE:**
- Specific protests/events mentioned by name and date
- Interview subjects named (worth Nate tracking down?)
- Organizations/funding sources mentioned (quote claims about them)
- Unanswered questions from their interviews Nate could ask
- Claims that need fact-checking (quote them)

CRITICAL: Use actual channel names, creator names, quotes from videos, and specific details. No generic descriptions.

Skip: entertainment, traditional commentary, anything not street-level investigative reporting.

TRANSCRIPTS:
{transcripts_list}

Output: Detailed tactical report (500-700 words) with specific names, quotes, and actionable intelligence."""
        
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
        print(f"ERROR generating report: {str(e)}")
        return None

def filter_relevant_videos(all_videos, max_count):
    """Use Claude to filter videos relevant to Nate Friedman's interests"""
    if not POE_API_KEY or not openai:
        return list(range(min(max_count, len(all_videos))))
    
    try:
        client = openai.OpenAI(
            api_key=POE_API_KEY,
            base_url="https://api.poe.com/v1",
        )
        
        # Build video list for filtering
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
5. Try to pick a representative sample of the stories

Ignore: General political commentary, entertainment, lifestyle, generic news coverage, celebrity content

VIDEO LIST:
{video_list}

Reply with ONLY the numbers of exactly {max_count} videos, separated by commas. For example: 1,3,5,7,9

Do not include any other text or explanation. You must return exactly {max_count} numbers."""
        
        chat = client.chat.completions.create(
            model="claude-haiku-4.5",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse the response
        response = chat.choices[0].message.content.strip()
        selected_indices = [int(x.strip()) - 1 for x in response.split(',')]
        return selected_indices
        
    except Exception as e:
        print(f"ERROR in filtering: {str(e)}")
        return list(range(min(max_count, len(all_videos))))

def get_video_transcript(video_title, video_url, channel_name):
    """Fetch full transcript from YouTube video with retry logic"""
    if not TRANSCRIPT_API_KEY:
        print(f"ERROR: TRANSCRIPT_API_KEY not found in environment")
        return None
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"ERROR: Could not extract video ID from {video_url}")
            return None
        
        print(f"Fetching transcript for video ID: {video_id}")
        
        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Fetch transcript from API using correct format
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
                        print(f"Rate limited for {video_id}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"ERROR: Rate limit exceeded for {video_id} after {max_retries} attempts")
                        return None
                
                if transcript_response.status_code != 200:
                    print(f"ERROR: Transcript API returned {transcript_response.status_code} for {video_id}")
                    return None
                
                data = transcript_response.json()
                
                # Extract transcript text using correct API structure
                if not data or len(data) == 0:
                    print(f"ERROR: No transcript data returned for video {video_id}")
                    return None
                
                if 'tracks' not in data[0]:
                    print(f"ERROR: No 'tracks' key found for video {video_id}")
                    return None
                    
                if len(data[0]['tracks']) == 0:
                    print(f"ERROR: Empty tracks array for video {video_id}")
                    return None
                
                if 'transcript' not in data[0]['tracks'][0]:
                    print(f"ERROR: No transcript in track for video {video_id}")
                    return None
                
                # Extract just the text, ignoring timestamps
                transcript_text = " ".join([segment["text"] for segment in data[0]["tracks"][0]["transcript"]])
                
                if not transcript_text.strip():
                    print(f"ERROR: Transcript is empty for video {video_id}")
                    return None
                
                print(f"Successfully fetched transcript for {video_id} ({len(transcript_text)} chars)")
                return transcript_text
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Request error for {video_id}, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
    except Exception as e:
        print(f"ERROR fetching transcript for {video_url}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    if not CHANNEL_IDS:
        print("⚠ Please add channel IDs to the CHANNEL_IDS dictionary at the top of the script!")
        return
    
    print(f"Checking {len(CHANNEL_IDS)} channels for videos from the last {DAYS_BACK} day(s)...")
    print("Using YouTube RSS feeds\n")
    print("=" * 80)
    
    results = []
    
    # Find channels with recent videos (in parallel, 20 at a time)
    print("Finding channels with recent videos...\n")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_channel = {
            executor.submit(check_channel_rss, name, cid, days=DAYS_BACK): name 
            for name, cid in CHANNEL_IDS.items()
        }
        
        completed = 0
        total = len(future_to_channel)
        
        for future in as_completed(future_to_channel):
            completed += 1
            channel_name = future_to_channel[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"[{completed}/{total}] ✓ {channel_name}: {len(result['videos'])} recent video(s)")
                else:
                    print(f"[{completed}/{total}] ✗ {channel_name}: No recent videos")
            except Exception as e:
                print(f"[{completed}/{total}] ✗ {channel_name}: Error")
    
    print("\n" + "=" * 80)
    print(f"\nFound {len(results)} channels with videos from the last {DAYS_BACK} day(s)")
    
    if not results:
        print(f"\n⚠ No recent videos found. Try increasing the DAYS_BACK constant.")
        return
    
    # Collect all videos
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
    
    print(f"Total videos found: {len(all_videos)}")
    
    # Sort by most recent
    all_videos.sort(key=lambda x: x['published'], reverse=True)
    
    # Filter videos to only those relevant to Nate Friedman's interests
    # Claude will select at most MAX_VIDEOS from all available videos
    print(f"\nFiltering {len(all_videos)} videos for relevance to Nate Friedman's interests...")
    selected_indices = filter_relevant_videos(all_videos, MAX_VIDEOS)
    selected_videos = [all_videos[i] for i in selected_indices if i < len(all_videos)]
    all_videos = selected_videos
    print(f"Selected {len(all_videos)} relevant videos for summary fetching")
    
    # Fetch transcripts for all videos (sequential with delay to avoid rate limiting)
    successful_transcripts = 0
    if FETCH_SUMMARIES:  # Using same config flag
        print("\nFetching video transcripts with rate limiting...")
        print("Processing sequentially with delays to avoid API rate limits\n")
        
        completed = 0
        total = len(all_videos)
        
        for video in all_videos:
            completed += 1
            try:
                transcript = get_video_transcript(video['title'], video['url'], video['channel'])
                if transcript:
                    video['transcript'] = transcript
                    successful_transcripts += 1
                    print(f"[{completed}/{total}] ✓ {video['title'][:50]}...")
                else:
                    video['transcript'] = None
                    print(f"[{completed}/{total}] ✗ {video['title'][:50]}...")
                
                # Add delay between requests to avoid rate limiting (except for last item)
                if completed < total:
                    time.sleep(1.5)  # 1.5 second delay between requests
                    
            except Exception as e:
                video['transcript'] = None
                print(f"[{completed}/{total}] ✗ {video['title'][:50]}... (Error)")
        
        print(f"\nSuccessfully fetched {successful_transcripts}/{len(all_videos)} transcripts")
    else:
        for video in all_videos:
            video['transcript'] = None
    
    # Generate daily report from all transcripts
    print("\nGenerating daily report from all transcripts...")
    daily_report = generate_daily_report(all_videos)
    
    # Save videos list to file
    output_file = f"videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write(f"YouTube Videos & Daily Report - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Videos from the last {DAYS_BACK} day(s) (max {MAX_VIDEOS})\n")
        f.write(f"Transcripts: {successful_transcripts}/{len(all_videos)}\n")
        f.write("=" * 100 + "\n\n")
        
        # Write the daily report at the top
        if daily_report:
            f.write("DAILY REPORT\n")
            f.write("-" * 100 + "\n\n")
            f.write(daily_report)
            f.write("\n\n" + "=" * 100 + "\n\n")
        
        f.write("FULL TRANSCRIPTS\n")
        f.write("-" * 100 + "\n\n")
        
        for i, video in enumerate(all_videos, 1):
            f.write(f"{i}. {video['channel']}\n")
            f.write(f"   Title: {video['title']}\n")
            f.write(f"   Published: {video['published_str']}\n")
            f.write(f"   URL: {video['url']}\n")
            if video.get('transcript'):
                f.write(f"\n   TRANSCRIPT:\n   {video['transcript']}\n")
            f.write("\n" + "-" * 100 + "\n\n")
    
    print(f"\n✓ Video list saved to: {output_file}")
    
    # Display daily report
    if daily_report:
        print("\n" + "=" * 100)
        print("DAILY REPORT")
        print("=" * 100)
        print(daily_report)
    
    # Display preview
    print("\n" + "=" * 100)
    print(f"\nFinal list ({len(all_videos)} videos):\n")
    
    for i, video in enumerate(all_videos, 1):
        transcript_status = "✓" if video.get('transcript') else "✗"
        print(f"{i}. {video['channel']} {transcript_status}")
        print(f"   {video['title']}")
        print(f"   {video['published_str']}")
        print(f"   {video['url']}\n")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"\n✓ Completed in {time.time() - start_time:.2f} seconds")