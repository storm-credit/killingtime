# Scripts

## Current MVP

`process_youtube_url.py`

- fetches metadata for a YouTube URL
- checks requested subtitle languages
- downloads the video
- downloads available subtitle files as `.srt`
- writes a summary report to `outputs/reports/`

Example:

```powershell
py scripts/process_youtube_url.py "https://www.youtube.com/watch?v=1CELx9LRI-Y"
```
