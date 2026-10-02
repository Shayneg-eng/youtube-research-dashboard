# Nate's Research Dashboard

A Next.js dashboard that displays recent YouTube videos from multiple channels focused on investigative journalism, street reporting, and exposing funding trails.

## Features

- **Python Backend**: `youtube_research_api.py` fetches videos from 24+ YouTube channels using RSS feeds
- **AI-Powered Filtering**: Uses Claude (via Poe API) to filter and prioritize the most relevant videos
- **Video Summaries**: Optionally fetches AI-generated summaries for each video using Perplexity
- **Clean Interface**: Modern, dark-themed dashboard built with Next.js and Tailwind CSS
- **Real-time Updates**: Refresh button to fetch the latest videos on demand

## Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Configure Environment Variables**
   
   The `.env.local` file should contain:
   ```
   POE_API_KEY=your_poe_api_key_here
   ```

3. **Ensure Python Dependencies**
   ```bash
   pip install requests openai python-dotenv
   ```

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.js`. The page auto-updates as you edit the file.

## How It Works

1. **Frontend** ([app/page.js](app/page.js))
   - React component that fetches video data from the API
   - Displays videos in a card-based layout with thumbnails and summaries
   - Includes refresh functionality

2. **API Route** ([app/api/videos/route.js](app/api/videos/route.js))
   - Next.js API endpoint that executes the Python backend
   - Returns JSON data to the frontend

3. **Python Backend** ([youtube_research_api.py](youtube_research_api.py))
   - Fetches RSS feeds from 24+ YouTube channels in parallel
   - Filters videos from the last 1 day (configurable)
   - Uses Claude to select the most relevant videos
   - Optionally fetches AI summaries using Perplexity
   - Returns structured JSON output

## Configuration

Edit [youtube_research_api.py](youtube_research_api.py) to customize:

- `MAX_VIDEOS`: Maximum number of videos to display (default: 50)
- `DAYS_BACK`: How many days back to look for videos (default: 1)
- `FETCH_SUMMARIES`: Whether to fetch AI summaries (default: True)
- `CHANNEL_IDS`: Add or remove YouTube channels to monitor

## Original Research Script

The original [youtube_research.py](youtube_research.py) file generates detailed text reports and is still available for standalone use.

## Tech Stack

- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **Backend**: Python 3, OpenAI SDK (for Poe API)
- **APIs**: YouTube RSS feeds, Poe API (Claude + Perplexity)

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!
