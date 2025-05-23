# Story Generation Service

## Overview
The Story Generation Service provides a REST interface for generating cinematic stories using the Anthropic Claude API. It supports detailed character descriptions, scene sequences, and narrative elements with structured output.

## API Endpoints

### `POST /generate-cinematic-story`
Generates a complete cinematic story with characters and scenes.

#### Request Body
```json
{
    "genre": "string",
    "total_chunks": "number",
    "previous_character": {
        "base_traits": "string",
        "facial_features": "string",
        "clothing": "string",
        "distinctive_features": "string"
    },
    "previous_sequence": [
        {
            "sequence_number": "number",
            "clip_duration": "number",
            "clip_action": "string",
            "voice_narration": "string",
            "type": "string",
            "environment": "string",
            "atmosphere": "string"
        }
    ]
}
```

#### Response
```json
{
    "movie_info": {
        "genre": "string",
        "title": "string",
        "description": "string",
        "release_year": "number",
        "director": "string",
        "rating": "number"
    },
    "character": {
        "base_traits": "string",
        "facial_features": "string",
        "distinctive_features": "string",
        "clothing": "string"
    },
    "music_score": {
        "type": "string",
        "style": "string",
        "tempo": "string",
        "instrumentation": "string"
    },
    "sequence": [
        {
            "sequence_number": "number",
            "clip_duration": "number",
            "clip_action": "string",
            "voice_narration": "string",
            "type": "string",
            "environment": "string",
            "atmosphere": "string"
        }
    ]
}
```

### `GET /health`
Health check endpoint.

#### Response
```json
{
    "status": "healthy"
}
```

## Story Generation Parameters

### Movie Info Requirements
```json
{
    "genre": "Must match requested genre exactly",
    "title": "Compelling, genre-appropriate title",
    "description": "2-3 sentence synopsis",
    "release_year": "Current year (2025)",
    "director": "Realistic director name",
    "rating": "Between 7.0 and 9.5"
}
```

### Character Data Structure
```json
{
    "base_traits": {
        "physical_attributes": {
            "age": "Age range or specific age",
            "ethnicity": "Ethnicity/background",
            "gender": "Gender",
            "body_type": "Body type and build",
            "proportions": "Height and proportions"
        },
        "format": "age, ethnicity, gender, body type, build"
    },
    "facial_features": {
        "eye_details": {
            "shape": "Shape and color",
            "expression": "Expression quality",
            "position": "Eye spacing and position"
        },
        "facial_structure": {
            "bone_structure": "Bone structure",
            "feature_placement": "Feature placement",
            "symmetry": "Overall symmetry"
        },
        "skin_quality": {
            "texture": "Texture and tone",
            "features": "Notable features",
            "age_indicators": "Age indicators"
        }
    },
    "clothing": {
        "primary_garments": {
            "material": "Material and texture",
            "style": "Style and cut",
            "color": "Color and pattern"
        },
        "fit": {
            "sitting": "How clothing sits on body",
            "condition": "Wear and tear",
            "movement": "Movement quality"
        },
        "accessories": {
            "jewelry": "Jewelry and adornments",
            "items": "Practical items",
            "pieces": "Character-defining pieces"
        }
    },
    "distinctive_features": {
        "unique_elements": {
            "traits": "Unusual physical traits",
            "markings": "Notable markings",
            "characteristics": "Distinctive characteristics"
        },
        "hair_details": {
            "style": "Style and cut",
            "color": "Color and texture",
            "movement": "Movement quality"
        },
        "special_features": {
            "modifications": "Piercings, Tattoos or modifications",
            "elements": "Character-defining elements",
            "details": "Memorable details"
        }
    }
}
```

### Scene Data Structure
```json
{
    "pose": {
        "base_posture": {
            "position": "Standing, sitting, kneeling, etc.",
            "direction": "Direction relative to light/camera",
            "stance": "Tense, relaxed, etc."
        },
        "facial_expression": {
            "eyes": "Eye direction and focus",
            "mouth": "Mouth position",
            "expression": "Overall expression"
        },
        "body_position": {
            "gestures": "Specific gestures",
            "orientation": "Body orientation",
            "movement": "Movement state"
        },
        "light_interaction": {
            "lighting": "How pose interacts with lighting",
            "shadows": "Shadow placement",
            "highlights": "Highlight positions"
        }
    }
}
```

## Error Handling
- Input validation for required fields
- API key validation
- Response parsing
- Claude API error management
- Detailed error logging

## Example Usage
```python
# Generate a cinematic story
response = requests.post(
    "http://localhost:5000/generate-cinematic-story",
    json={
        "genre": "noir",
        "total_chunks": 1,
        "previous_character": None,
        "previous_sequence": None
    }
)

# Check service health
health = requests.get("http://localhost:5000/health")
```

## Dependencies
- Flask: Web framework
- Anthropic: Claude API
- Python-dotenv: Environment management
- Logging: Error tracking
- JSON: Response parsing

## Performance Considerations
- Chunked story generation
- Response parsing optimization
- Memory management
- Error recovery mechanisms
- Request timeout handling

## Best Practices
1. Validate all input parameters
2. Use appropriate generation settings
3. Monitor API usage and limits
4. Implement proper error handling
5. Maintain consistent response format
6. Monitor system resources
7. Implement proper cleanup
8. Track generation progress

## Security Considerations
1. API key protection
2. Input sanitization
3. Response validation
4. Rate limiting
5. Error message sanitization

## Monitoring
- Request logging
- Error tracking
- Performance metrics
- Resource usage
- API response times 