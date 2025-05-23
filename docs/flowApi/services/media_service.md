# Media Service

## Overview
The Media Service handles video and audio processing operations, including video merging, concatenation, and format conversion. It provides essential media manipulation capabilities for the video generation pipeline.

## Features
- Video merging with audio
- Video concatenation
- Format conversion
- Resolution management
- Frame rate control

## Functions

### `merge_video_audio(video_path, audio_path, output_path)`
Merges video and audio files into a single video file.
- **Parameters:**
  - `video_path` (str): Path to video file
  - `audio_path` (str): Path to audio file
  - `output_path` (str): Output file path
- **Returns:**
  - `bool`: Success status
- **Video Specifications:**
  - Codec: H.264
  - Container: MP4
  - Pixel Format: yuv420p
  - CRF: 5 (High Quality)

### `concatenate_videos(video_paths, output_path)`
Concatenates multiple videos into a single video file.
- **Parameters:**
  - `video_paths` (list): List of video file paths
  - `output_path` (str): Output file path
- **Returns:**
  - `bool`: Success status
- **Processing:**
  - Maintains consistent format
  - Preserves audio tracks
  - Handles transitions

## Video Processing Parameters
```json
{
    "video": {
        "codec": "h264",
        "pixel_format": "yuv420p",
        "crf": 5,
        "preset": "medium",
        "resolution": "1920x1080",
        "fps": 24
    },
    "audio": {
        "codec": "aac",
        "sample_rate": 44100,
        "channels": 2,
        "bitrate": "192k"
    }
}
```

## Supported Formats
### Input
- Video: MP4, MOV, AVI
- Audio: WAV, MP3, AAC

### Output
- Video: MP4 (H.264)
- Audio: AAC

## Error Handling
- Validates input files
- Checks format compatibility
- Manages temporary files
- Provides detailed error messages

## Example Usage
```python
# Merge video and audio
success = merge_video_audio(
    video_path="video.mp4",
    audio_path="audio.wav",
    output_path="final.mp4"
)

# Concatenate multiple videos
success = concatenate_videos(
    video_paths=["scene1.mp4", "scene2.mp4", "scene3.mp4"],
    output_path="complete.mp4"
)
```

## Dependencies
- FFmpeg: Media processing
- subprocess: Command execution
- os: File operations
- logging: Error tracking

## Performance Considerations
- Optimizes encoding settings
- Manages memory usage
- Implements progress tracking
- Handles large files efficiently

## Best Practices
1. Always validate input files before processing
2. Use appropriate video codec settings for quality
3. Monitor system resources during processing
4. Implement proper cleanup of temporary files
5. Use error handling for all operations 