# Narration Service

## Overview
The Narration Service handles text-to-speech generation for video narration, providing voice synthesis with character-appropriate voice selection and duration management.

## Features
- Text-to-speech generation with multiple voice options
- Character-based voice selection
- Text duration estimation and adjustment
- Silent audio generation for empty narration
- Voice consistency maintenance

## API Integration
- Endpoint: `http://localhost:5010/generate-voice`
- Method: POST
- Content-Type: application/json

## Functions

### `estimate_text_duration(text)`
Estimates the duration of text based on average speaking rate.
- **Parameters:**
  - `text` (str): The text to estimate duration for
- **Returns:**
  - `float`: Estimated duration in seconds
- **Note:** Uses average speaking rate of 150 words per minute

### `adjust_text_for_duration(text, target_duration)`
Adjusts text to fit within target duration while maintaining coherence.
- **Parameters:**
  - `text` (str): Original text
  - `target_duration` (float): Target duration in seconds
- **Returns:**
  - `str`: Adjusted text
- **Note:** Maintains minimum 3 words for coherence

### `select_voice(character_data)`
Selects appropriate voice based on character traits.
- **Parameters:**
  - `character_data` (dict): Character information including base traits
- **Returns:**
  - `str`: Selected voice identifier
- **Voice Options:**
  - Female voices: "female1", "female2", "female3"
  - Male voices: "male1", "male2", "male3"
  - Default: "me"

### `generate_narration(text, image_path, output_folder, logger, character_data, selected_voice)`
Generates narration audio using TTS API.
- **Parameters:**
  - `text` (str): Narration text
  - `image_path` (str): Path to associated image
  - `output_folder` (str): Output directory
  - `logger` (Logger): Logging instance
  - `character_data` (dict): Character information
  - `selected_voice` (str): Optional pre-selected voice
- **Returns:**
  - `tuple`: (success: bool, message: str)
- **Output:**
  - WAV file in output folder
  - Sample rate: 22050 Hz
  - Channels: Mono
  - Format: PCM 16-bit

## Error Handling
- Handles empty narration with silent audio generation
- Validates file creation with timeout
- Provides detailed error messages
- Implements retry mechanisms for API calls

## Example Usage
```python
# Generate narration for a scene
success, message = generate_narration(
    text="The hero stood tall against the setting sun.",
    image_path="scene_001.png",
    output_folder="output/",
    logger=logging.getLogger(__name__),
    character_data={"base_traits": "male hero"}
)
```

## Dependencies
- requests: API communication
- subprocess: FFmpeg integration
- logging: Error tracking
- os: File operations
- time: Timing and delays 