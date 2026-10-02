'use client';
import { useState, useEffect } from 'react';

export default function Home() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [dailyReport, setDailyReport] = useState(null);

  useEffect(() => {
    fetchVideos();
  }, []);

  async function fetchVideos() {
    try {
      setLoading(true);
      const response = await fetch('/api/videos');
      
      if (!response.ok) {
        throw new Error('Failed to fetch videos');
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      setVideos(data.videos || []);
      setDailyReport(data.report || null);
      setMetadata({
        generated: data.generated,
        totalChannels: data.total_channels,
        channelsWithVideos: data.channels_with_videos,
        daysBack: data.days_back,
        transcriptsFetched: data.transcripts_fetched
      });
      setLoading(false);
    } catch (error) {
      console.error('Error fetching videos:', error);
      setError(error.message);
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <h1 className="text-4xl font-bold mb-8">Nate's Research Dashboard</h1>
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
          <p>Analyzing videos from {metadata?.totalChannels || 'multiple'} channels and fetching transcripts...</p>
        </div>
        <p className="text-sm text-gray-500 mt-2">This may take 1-2 minutes to fetch transcripts and generate report</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <h1 className="text-4xl font-bold mb-8">Nate's Research Dashboard</h1>
        <div className="bg-red-900/50 border border-red-500 p-4 rounded-lg">
          <p className="font-semibold mb-2">Error loading videos</p>
          <p className="text-sm">{error}</p>
          <button 
            onClick={fetchVideos}
            className="mt-4 bg-red-700 hover:bg-red-600 px-4 py-2 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-4">Nate's Research Dashboard</h1>
          {metadata && (
            <div className="flex gap-6 text-sm text-gray-400">
              <div>
                <span className="font-semibold text-gray-300">{videos.length}</span> videos found
              </div>
              <div>
                <span className="font-semibold text-gray-300">{metadata.transcriptsFetched || 0}</span> transcripts fetched
              </div>
              <div>
                <span className="font-semibold text-gray-300">{metadata.channelsWithVideos}</span> / {metadata.totalChannels} channels active
              </div>
              <div>
                Last <span className="font-semibold text-gray-300">{metadata.daysBack}</span> day(s)
              </div>
              <button 
                onClick={fetchVideos}
                className="ml-auto text-blue-400 hover:text-blue-300 flex items-center gap-1"
              >
                <span>↻</span> Refresh
              </button>
            </div>
          )}
        </div>

        {/* Daily Report Section */}
        {dailyReport && (
          <div className="mb-8 bg-gradient-to-br from-blue-900/40 to-purple-900/40 border border-blue-700/50 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
              <span>📊</span> Daily Intelligence Report
            </h2>
            <div className="prose prose-invert max-w-none">
              <div className="whitespace-pre-wrap text-gray-300 leading-relaxed">
                {dailyReport}
              </div>
            </div>
          </div>
        )}
        
        {videos.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No videos found in the last {metadata?.daysBack || 1} day(s)</p>
          </div>
        ) : (
          <div>
            <h2 className="text-2xl font-bold mb-4">Individual Video Details</h2>
            <div className="space-y-4">
              {videos.map((video, index) => (
                <div key={video.videoId || index} className="bg-gray-800 rounded-lg overflow-hidden hover:bg-gray-750 transition-colors border border-gray-700">
                  <a 
                    href={video.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex gap-4 p-4"
                  >
                    <div className="flex-shrink-0">
                      <img 
                        src={`https://i.ytimg.com/vi/${video.videoId}/mqdefault.jpg`}
                        alt={video.title} 
                        className="w-48 h-28 object-cover rounded"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-semibold text-blue-400">{video.channel}</span>
                        <span className="text-xs text-gray-500">•</span>
                        <span className="text-xs text-gray-500">{video.published_str}</span>
                      </div>
                      <h2 className="text-lg font-semibold mb-3 line-clamp-2">{video.title}</h2>
                      {video.transcript ? (
                        <div className="bg-gray-900/50 p-3 rounded border border-gray-700">
                          <details className="text-sm text-gray-300">
                            <summary className="cursor-pointer font-semibold text-blue-400 hover:text-blue-300 mb-2">View Full Transcript</summary>
                            <p className="leading-relaxed whitespace-pre-wrap mt-2 max-h-96 overflow-y-auto">
                              {video.transcript}
                            </p>
                          </details>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 italic">No transcript available</p>
                      )}
                    </div>
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}