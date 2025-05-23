# Video Generation Service

## Overview
The Video Generation Service orchestrates the creation of videos from images, including narration, background music, and effects. It coordinates with multiple services to produce the final video output.

## API Endpoints

### `POST /generateVideos/<folder_id>`
Generates videos from images in the specified folder.

#### Request Body
```json
{
    "sequence_data": [
        {
            "scene_number": "number",
            "narration": "string",
            "duration": "number",
            "clip_action": "string",
            "music_mood": "string"
        }
    ],
    "generation_params": {
        "transition_type": "string",
        "seed": "number",
        "fps": "number"
    }
}
```

#### Response
```json
{
    "success": "boolean",
    "video_url": "string",
    "metadata": {
        "duration": "number",
        "scenes": "number",
        "timestamp": "string"
    }
}
```

## Core Functions

### `process_video_generation(folder_id, data)`
Main orchestrator for video generation process.
- **Parameters:**
  - `folder_id` (str): Folder containing images
  - `data` (dict): Generation parameters
- **Returns:**
  - `tuple`: (success: bool, video_url: str)

### `generate_video(image_path, output_path, clip_duration, clip_action, seed)`
Generates a single video clip from an image.
- **Parameters:**
  - `image_path` (str): Source image path
  - `output_path` (str): Output video path
  - `clip_duration` (float): Duration in seconds
  - `clip_action` (str): Movement description
  - `seed` (int): Random seed
- **Returns:**
  - `bool`: Success status

### `validate_clip_action(clip_action, duration)`
Validates and simplifies clip actions based on duration.
- **Parameters:**
  - `clip_action` (str): Original clip action
  - `duration` (float): Clip duration
- **Returns:**
  - `str`: Validated clip action

## Video Generation Parameters
```json
{
    "video": {
        "resolution": {
            "width": 1024,
            "height": 576
        },
        "fps": 24,
        "codec": "h264",
        "pixel_format": "yuv420p",
        "crf": 5
    },
    "animation": {
        "max_duration": 6.0,
        "transition_types": ["none", "fade", "crossfade"],
        "movement_limits": {
            "3": 1,
            "5": 2,
            "7": 3
        }
    }
}
```

## Service Integration

### Narration Service
- Text-to-speech generation
- Voice selection
- Duration management

### Music Service
- Background music generation
- Mood-based selection
- Volume mixing

### Media Service
- Video processing
- Audio mixing
- Format conversion

## Error Handling
- Input validation
- Service availability checks
- File system management
- Progress tracking
- Error recovery

## Example Usage
```python
# Generate a video sequence
response = requests.post(
    "http://localhost:5000/generateVideos/movie_123",
    json={
        "sequence_data": [
            {
                "scene_number": 1,
                "narration": "The hero stood tall against the setting sun.",
                "duration": 5,
                "clip_action": "slow zoom out, pan right",
                "music_mood": "epic"
            }
        ],
        "generation_params": {
            "transition_type": "fade",
            "seed": 12345,
            "fps": 24
        }
    }
)
```

## Dependencies
- Flask: Web framework
- ComfyUI: Video generation
- FFmpeg: Media processing
- Firebase: Storage
- Python-dotenv: Environment management

## Performance Considerations
- Parallel processing
- Resource management
- Memory optimization
- Progress tracking
- Error recovery

## Best Practices
1. Validate all input parameters
2. Monitor system resources
3. Implement proper error handling
4. Use appropriate video settings
5. Maintain consistent file naming
6. Implement proper cleanup
7. Monitor service health
8. Track generation progress 