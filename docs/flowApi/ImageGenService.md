# Image Generation Service

## Overview
The Image Generation Service is responsible for creating images using ComfyUI, managing character and scene prompts, and handling image storage in Firebase. It provides a REST API for image generation requests.

## API Endpoints

### `POST /generateImages`
Generates images based on provided prompts and character data.

#### Request Body
```json
{
    "character_data": {
        "base_traits": "string",
        "facial_features": "string",
        "clothing": "string",
        "distinctive_features": "string"
    },
    "sequence_data": [
        {
            "scene_description": "string",
            "atmosphere": "string",
            "duration": "number"
        }
    ],
    "generation_params": {
        "seed": "number",
        "sampler": "string",
        "steps": "number",
        "cfg_scale": "number"
    }
}
```

#### Response
```json
{
    "success": "boolean",
    "folder_id": "string",
    "image_urls": [
        {
            "scene_number": "number",
            "url": "string"
        }
    ],
    "metadata": {
        "timestamp": "string",
        "total_scenes": "number"
    }
}
```

## Core Functions

### `build_character_prompt(character_data)`
Constructs a structured character prompt with weighted emphasis on key features.
- **Parameters:**
  - `character_data` (dict): Character information
- **Returns:**
  - `str`: Formatted character prompt

### `filter_duplicate_traits(character_prompt, atmosphere)`
Removes duplicate traits and adds color balance.
- **Parameters:**
  - `character_prompt` (str): Character prompt
  - `atmosphere` (str): Scene atmosphere
- **Returns:**
  - `str`: Filtered and balanced prompt

### `build_image_workflow(sequence_data, character_data, seed, sampler, steps, cfg_scale, output_folder, global_negative_prompt)`
Constructs the ComfyUI workflow for image generation.
- **Parameters:**
  - `sequence_data` (list): Scene sequence data
  - `character_data` (dict): Character information
  - `seed` (int): Random seed
  - `sampler` (str): Sampler type
  - `steps` (int): Generation steps
  - `cfg_scale` (float): CFG scale
  - `output_folder` (str): Output directory
  - `global_negative_prompt` (str): Global negative prompt
- **Returns:**
  - `dict`: ComfyUI workflow configuration

## Image Generation Parameters
```json
{
    "model": "sd3.5_large_fp8_scaled.safetensors",
    "resolution": {
        "width": 1024,
        "height": 576
    },
    "sampling": {
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler": "euler_ancestral"
    }
}
```

## Error Handling
- Input validation
- API timeout management
- File system error handling
- Firebase connection errors
- Generation failure recovery

## Example Usage
```python
# Generate images for a scene
response = requests.post(
    "http://localhost:5000/generateImages",
    json={
        "character_data": {
            "base_traits": "young female warrior",
            "facial_features": "determined expression, long hair",
            "clothing": "leather armor, red cloak",
            "distinctive_features": "scar on cheek, golden amulet"
        },
        "sequence_data": [
            {
                "scene_description": "standing on cliff edge",
                "atmosphere": "sunset, dramatic lighting",
                "duration": 5
            }
        ],
        "generation_params": {
            "seed": 12345,
            "sampler": "euler_ancestral",
            "steps": 20,
            "cfg_scale": 7.0
        }
    }
)
```

## Dependencies
- Flask: Web framework
- ComfyUI: Image generation
- Firebase: Storage and database
- FFmpeg: Image processing
- Python-dotenv: Environment management

## Performance Considerations
- Parallel image generation
- Resource management
- Caching mechanisms
- Error recovery
- Progress tracking

## Best Practices
1. Validate all input parameters
2. Implement proper error handling
3. Monitor system resources
4. Use appropriate image settings
5. Maintain consistent file naming 