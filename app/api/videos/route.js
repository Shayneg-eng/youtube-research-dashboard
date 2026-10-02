import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execPromise = promisify(exec);

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Path to the Python script
    const scriptPath = path.join(process.cwd(), 'youtube_research_api.py');
    
    // Execute the Python script
    const { stdout, stderr } = await execPromise(`python "${scriptPath}"`, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large outputs
    });
    
    if (stderr) {
      console.error('Python stderr:', stderr);
    }
    
    // Parse the JSON output
    const data = JSON.parse(stdout);
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error executing Python script:', error);
    return NextResponse.json(
      { error: 'Failed to fetch video data', details: error.message },
      { status: 500 }
    );
  }
}
