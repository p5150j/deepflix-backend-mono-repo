# Music Service

## Overview
The Music Service handles background music generation and integration for videos, providing mood-appropriate music scores and seamless audio mixing.

## Features
- Background music generation based on scene mood
- Music duration management
- Audio mixing with narration
- Volume normalization
- Multiple music style support

## API Integration
- Endpoint: `http://localhost:5009/generate`
- Method: POST
- Content-Type: application/json

## Functions

### `generate_music_score(mood, duration, output_folder)`
Generates background music based on mood and duration.
- **Parameters:**
  - `mood` (str): Desired mood of the music
  - `duration` (float): Duration in seconds
  - `output_folder` (str): Output directory
- **Returns:**
  - `tuple`: (success: bool, file_path: str)
- **Supported Moods:**
  - Action
  - Drama
  - Suspense
  - Romance
  - Comedy
  - Documentary

### `add_background_music(video_path, music_path, output_path, volume=0.3)`
Mixes background music with video audio.
- **Parameters:**
  - `video_path` (str): Path to video file
  - `music_path` (str): Path to music file
  - `output_path` (str): Output file path
  - `volume` (float): Music volume (0.0 to 1.0)
- **Returns:**
  - `bool`: Success status
- **Audio Processing:**
  - Normalizes audio levels
  - Applies crossfade
  - Maintains narration clarity

## Music Generation Parameters
```json
{
    "mood": "action",
    "duration": 30.0,
    "style": "cinematic",
    "instruments": ["strings", "percussion"],
    "tempo": "moderate",
    "intensity": 0.7
}
```

## Audio Specifications
- Format: WAV
- Sample Rate: 44100 Hz
- Channels: Stereo
- Bit Depth: 16-bit

## Error Handling
- Validates input parameters
- Handles API timeouts
- Manages file system errors
- Provides detailed error logging

## Example Usage
```python
# Generate and add background music
success, music_path = generate_music_score(
    mood="action",
    duration=30.0,
    output_folder="output/"
)

if success:
    add_background_music(
        video_path="video.mp4",
        music_path=music_path,
        output_path="final_video.mp4",
        volume=0.3
    )
```

## Dependencies
- requests: API communication
- subprocess: FFmpeg integration
- logging: Error tracking
- os: File operations
- json: Parameter handling

## Performance Considerations
- Caches generated music
- Optimizes audio processing
- Manages memory usage
- Implements timeout handling 