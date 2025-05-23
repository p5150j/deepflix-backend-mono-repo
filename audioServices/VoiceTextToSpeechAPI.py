import os
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import logging
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get ElevenLabs API key from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    logger.error("ElevenLabs API key not found in .env file")
    raise ValueError("ELEVENLABS_API_KEY environment variable not set")

# Initialize ElevenLabs client
client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

# Voice mapping - maps your system's voice names to ElevenLabs voice IDs
VOICE_MAPPING = {
    "male1": "YmP1fAL2C7KGze05u879",  # Your preferred voice
    "male2": "NFG5qt843uXKj4pFvR7C", 
    "male3": "vNm4u40hTe4NQoRG82Bs",
    "female1": "gmv0PPPs8m6FEf03PImj",
    "female2": "ZF6FPAbjXT4488VcRRnw",
    "female3": "tQ4MEZFJOzsahSEEZtHK",
    # Add more voice mappings as needed
    "default": "EXAVITQu4vr4xnSDxMaL"  # Default fallback voice
}

@app.route('/generate-voice', methods=['POST'])
def generate_voice():
    try:
        # Get JSON payload from request
        payload = request.json
        logger.info(f"Received payload: {payload}")
        
        # Validate required fields according to your pipeline's format
        required_fields = ["text", "voice", "filename", "filepath"]
        for field in required_fields:
            if field not in payload:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Extract data from payload using your pipeline's format
        text = payload["text"]
        voice_name = payload["voice"]
        file_name = payload["filename"]
        output_dir = payload["filepath"]
        
        # Map the voice name to ElevenLabs voice ID
        voice_id = VOICE_MAPPING.get(voice_name, VOICE_MAPPING["default"])
        
        # Set fixed parameters for ElevenLabs
        model_id = "eleven_turbo_v2"
        output_format = "mp3_22050_32"  # Using WAV format
        optimize_streaming_latency = "0"
        
        # Fixed voice settings
        voice_settings = VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
        )
        
        # Ensure the output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Full path for the output audio file
        output_file_path = output_path / f"{file_name}.wav"
        
        logger.info(f"Generating voice using ElevenLabs SDK: {voice_id} for text: '{text}'")
        
        # Call the ElevenLabs SDK
        response = client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency=optimize_streaming_latency,
            output_format=output_format,
            text=text,
            model_id=model_id,
            voice_settings=voice_settings,
        )
        
        # Save the audio file
        with open(output_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Successfully generated voice and saved to {output_file_path}")
        
        # Return success response
        return jsonify({
            "status": "success",
            "message": "Voice generated successfully",
            "file_path": str(output_file_path)
        })
    
    except Exception as e:
        logger.exception("Error in generate_voice endpoint")
        return jsonify({"error": str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    """Get available voices from ElevenLabs and map to internal voice names"""
    try:
        elevenlabs_voices = client.voices.get_all()
        
        # Create a simple mapping that your system can understand
        system_voices = {
            name: voice_id for name, voice_id in VOICE_MAPPING.items()
        }
        
        return jsonify({
            "elevenlabs_voices": elevenlabs_voices,
            "system_voices": system_voices
        })
    
    except Exception as e:
        logger.exception("Error in list_voices endpoint")
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5010))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.run(host="0.0.0.0", port=port, debug=debug)