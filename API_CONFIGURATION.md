# API Configuration for Enhanced Music Discovery

The music discovery app supports integration with external music services to provide rich metadata enrichment. This document explains how to configure API access for enhanced functionality.

## Supported Services

### 1. MusicBrainz
- **Status**: Always enabled (no API key required)
- **Provides**: Artist IDs, album IDs, track IDs, artist metadata
- **Rate limit**: 1 request per second

### 2. Last.fm
- **Status**: Optional (requires API key)
- **Provides**: Artist biographies, tags, similar artists, play counts
- **Rate limit**: 2 requests per second

#### Configuration:
```bash
export LASTFM_API_KEY="your_lastfm_api_key_here"
```

To get a Last.fm API key:
1. Visit https://www.last.fm/api/account/create
2. Create an account or log in
3. Fill out the application form
4. Copy the API key (not the shared secret)

### 3. Discogs
- **Status**: Optional (requires API token)
- **Provides**: Artist discographies, release information, marketplace data
- **Rate limit**: ~1 request per 1.5 seconds

#### Configuration:
```bash
export DISCOGS_TOKEN="your_discogs_token_here"
```

To get a Discogs token:
1. Visit https://www.discogs.com/settings/developers
2. Create an account or log in
3. Generate a new token
4. Copy the token

## Usage Examples

### Basic Usage (Mock Data Only)
```bash
# Run without API keys - uses enhanced mock data
python3 music_discovery.py --windowed
```

### With Last.fm Integration
```bash
# Set API key and run
export LASTFM_API_KEY="your_key_here"
python3 music_discovery.py --windowed
```

### With All Services
```bash
# Set all API credentials
export LASTFM_API_KEY="your_lastfm_key"
export DISCOGS_TOKEN="your_discogs_token"
python3 music_discovery.py --windowed
```

### Using Environment File
Create a `.env` file:
```bash
# .env file
LASTFM_API_KEY=your_lastfm_api_key_here
DISCOGS_TOKEN=your_discogs_token_here
```

Then source it before running:
```bash
source .env
python3 music_discovery.py --windowed
```

## Service Status

The application will log the status of each service at startup:
- **MusicBrainz**: Always enabled
- **Last.fm**: "enabled with API" or "mock data only (no API key)"  
- **Discogs**: "enabled with API" or "mock data only (no token)"

## Mock Data vs Real Data

### Without API Keys:
- Services return realistic mock data for demonstration
- No external API calls are made
- Perfect for testing and development

### With API Keys:
- Real data from external services
- Artist biographies, actual discographies, real play counts
- Live similar artist recommendations
- Rate limiting and error handling

## Troubleshooting

### Common Issues:

1. **"Mock data only" messages**
   - Solution: Verify environment variables are set correctly
   - Check: `echo $LASTFM_API_KEY` and `echo $DISCOGS_TOKEN`

2. **API rate limiting errors**
   - Services have built-in rate limiting
   - Wait times are automatically managed
   - Check service status in debug logs

3. **Invalid API credentials**
   - Verify keys/tokens are correct and active
   - Check service-specific logs for error details

### Debug Mode:
```bash
python3 music_discovery.py --windowed --debug
```

This will show detailed logs for all enrichment operations.

## Privacy Notes

- API keys are used only for metadata enrichment
- No personal data is transmitted to external services
- Only artist, album, and track names are sent for lookup
- All API calls respect service rate limits and terms of use