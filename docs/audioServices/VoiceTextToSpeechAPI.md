# Voice Text-to-Speech API

## Overview
The Voice Text-to-Speech API provides a REST interface for converting text to speech using the ElevenLabs API. It supports multiple voices, customizable settings, and efficient audio file generation.

## API Endpoints

### `POST /generate-voice`
Generates voice audio from text using specified voice and settings.

#### Request Body
```json
{
    "text": "string",
    "voice": "string",
    "filename": "string",
    "filepath": "string"
}
```

#### Response
```json
{
    "status": "success",
    "message": "Voice generated successfully",
    "file_path": "string"
}
```

### `GET /voices`
Lists all available voices and their mappings.

#### Response
```json
{
    "elevenlabs_voices": [
        {
            "voice_id": "string",
            "name": "string",
            "settings": {
                "stability": "number",
                "similarity_boost": "number",
                "style": "number",
                "use_speaker_boost": "boolean"
            }
        }
    ],
    "system_voices": {
        "voice_name": "voice_id"
    }
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

## Voice Configuration

### Voice Mappings
```json
{
    "male1": "YmP1fAL2C7KGze05u879",
    "male2": "NFG5qt843uXKj4pFvR7C",
    "male3": "vNm4u40hTe4NQoRG82Bs",
    "female1": "gmv0PPPs8m6FEf03PImj",
    "female2": "ZF6FPAbjXT4488VcRRnw",
    "female3": "tQ4MEZFJOzsahSEEZtHK",
    "default": "EXAVITQu4vr4xnSDxMaL"
}
```

### Voice Settings
```json
{
    "stability": 0.0,
    "similarity_boost": 1.0,
    "style": 0.0,
    "use_speaker_boost": true
}
```

## Generation Parameters
```json
{
    "model_id": "eleven_turbo_v2",
    "output_format": "mp3_22050_32",
    "optimize_streaming_latency": "0"
}
```

## Error Handling
- Input validation for required fields
- API key validation
- File system error handling
- ElevenLabs API error management
- Detailed error logging

## Example Usage
```python
# Generate voice from text
response = requests.post(
    "http://localhost:5010/generate-voice",
    json={
        "text": "Hello, this is a test message.",
        "voice": "female1",
        "filename": "test_audio",
        "filepath": "output/"
    }
)

# List available voices
voices = requests.get("http://localhost:5010/voices")

# Check service health
health = requests.get("http://localhost:5010/health")
```

## Dependencies
- Flask: Web framework
- ElevenLabs: Text-to-speech API
- Python-dotenv: Environment management
- Logging: Error tracking
- Pathlib: File path handling

## Performance Considerations
- Streaming optimization for large texts
- Efficient file system operations
- Memory management for audio data
- Error recovery mechanisms
- Request timeout handling

## Best Practices
1. Validate all input parameters
2. Use appropriate voice settings
3. Monitor API usage and limits
4. Implement proper error handling
5. Maintain consistent file naming
6. Monitor system resources
7. Implement proper cleanup
8. Track generation progress

## Security Considerations
1. API key protection
2. Input sanitization
3. File path validation
4. Rate limiting
5. Error message sanitization

## Monitoring
- Request logging
- Error tracking
- Performance metrics
- Resource usage
- API response times 