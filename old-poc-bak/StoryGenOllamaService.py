from flask import Flask, request, jsonify
import json
import logging
import os
import math
import time
import requests
from dotenv import load_dotenv
from typing import Dict, Any

# Set up logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ollama_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi4')  # Changed to phi4

# Check if Ollama is accessible
try:
    response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
    logger.debug(f"Ollama available models: {response.json()}")
except Exception as e:
    logger.error(f"Failed to connect to Ollama: {str(e)}")

# System prompt for Mistral - simplified from original to work better with Mistral
system_prompt = """CRITICAL: Return ONLY the JSON structure below. Do not add any explanatory text, introductions, or additional formatting before or after the JSON. The response must start with { and end with }.

CRITICAL: JSON VALIDATION RULES:
1. The response must be a single, valid JSON object
2. No markdown formatting or HTML tags allowed
3. No explanatory text before or after the JSON
4. No line breaks or extra spaces in the JSON
5. All field names must be lowercase
6. All string values must be properly quoted
7. All numbers must be valid JSON numbers
8. No trailing commas in arrays or objects
9. No comments or annotations
10. The JSON must be parseable by standard JSON parsers

CRITICAL: JSON STRUCTURE VALIDATION:
1. The root object must have exactly these fields:
   - character (object)
   - music_score (object)
   - sequence (array)
2. Each sequence object must have exactly these fields:
   - sequence_number (number)
   - clip_duration (number)
   - clip_action (string)
   - voice_narration (string)
   - type (string)
   - environment (string)
   - atmosphere (string)
   - negative_prompt (string)
3. The character object must have exactly these fields:
   - base_traits (string)
   - facial_features (string)
   - distinctive_features (string)
   - clothing (string)
4. The music_score object must have exactly these fields:
   - type (string)
   - style (string)
   - tempo (string)
   - instrumentation (string)

CRITICAL: JSON VALUE VALIDATION:
1. sequence_number must be a positive integer
2. clip_duration must be a positive number between 2.0 and 7.0
3. type must be either "b-roll" or "character"
4. All string fields must be non-empty
5. All weighted terms must use the format "(term:1.4)"
6. No special characters in field names
7. No nested objects or arrays except for the sequence array
8. No null values allowed
9. No undefined values allowed
10. No duplicate sequence numbers

CRITICAL: Each sequence must contain unique, creative content. Do not use placeholder text or repeat the same content across sequences. Each sequence should advance the story with new, specific details.

CRITICAL: BATCH PROCESSING RULES:
1. Process sequences in logical groups of 3-4 shots
2. Each batch must maintain visual continuity
3. Each batch should advance the story meaningfully
4. Use consistent timing patterns within batches
5. Follow shot progression patterns within batches

CRITICAL: SHOT BATCHING PATTERNS:
1. Establishing Batch (3 shots):
   - Wide -> Wide -> Medium
   - Timing: 4s -> 4s -> 6s
   - Purpose: Set scene and introduce character

2. Action Batch (3 shots):
   - Medium -> Close -> Medium
   - Timing: 6s -> 3s -> 6s
   - Purpose: Show character action and reaction

3. Emotional Batch (3 shots):
   - Wide -> Close -> Wide
   - Timing: 4s -> 3s -> 4s
   - Purpose: Build emotional impact

4. Resolution Batch (3 shots):
   - Medium -> Wide -> Close
   - Timing: 6s -> 4s -> 3s
   - Purpose: Conclude story beat

CRITICAL: VISUAL CONTINUITY RULES:
1. Maintain consistent lighting style within batches
2. Keep character appearance consistent
3. Progress environment naturally
4. Match camera movements to emotional context
5. Use consistent color grading

CRITICAL: TIMING CONSISTENCY:
1. Wide shots: 4.0-6.0 seconds
2. Medium shots: 6.0-7.0 seconds
3. Close-ups: 2.0-3.0 seconds
4. Action shots: 3.0-4.0 seconds
5. Emotional shots: 4.0-5.0 seconds

Return this exact JSON structure with your story content. Do not add any other text or formatting:

{
    "character": {
        "base_traits": "(mid-30s asian woman:1.4)",
        "facial_features": "(determined brown eyes:1.3)",
        "distinctive_features": "(small scar on left cheek:1.4)",
        "clothing": "(hiking gear:1.2)"
    },
    "music_score": {
        "type": "ambient",
        "style": "dark, ominous, suspenseful",
        "tempo": "slow, steady, building tension",
        "instrumentation": "piano, strings, electronic elements"
    },
    "sequence": [
        {
            "sequence_number": 1,
            "clip_duration": 3.0625,
            "clip_action": "static camera, clouds drifting slowly",
            "voice_narration": "...",
            "type": "b-roll",
            "environment": "ESTABLISHING SHOT - EXT. COLORADO MOUNTAINS - DAY",
            "atmosphere": "(8k uhd:1.4), (photorealistic:1.4), (cinematic lighting:1.3), (film grain:1.2), (cinematic color grading:1.3), (somber mood:1.4)",
            "negative_prompt": "(worst quality:1.4), (low quality:1.4), (blurry:1.2), (deformed:1.4), (distorted:1.4), (bad anatomy:1.4), (bad proportions:1.4), (multiple people:1.8), (wrong face:1.8), (different person:1.8), (duplicate body parts:1.4), (missing limbs:1.4), (bad hands:1.4)"
        },
        {
            "sequence_number": 2,
            "clip_duration": 3.0625,
            "clip_action": "pan right, leaves swaying gently",
            "voice_narration": "It has to be here somewhere...",
            "type": "character",
            "pose": "[previous character traits], (sitting on rock:1.4), (leaning forward slightly:1.3)",
            "environment": "MEDIUM SHOT - EXT. COLORADO MOUNTAINS - DAY",
            "atmosphere": "(frustrated determination:1.4), (dramatic sunset light:1.4), (golden hour:1.3)",
            "negative_prompt": "(worst quality:1.4), (low quality:1.4), (blurry:1.2), (deformed:1.4), (distorted:1.4), (bad anatomy:1.4), (bad proportions:1.4), (multiple people:1.8), (wrong face:1.8), (different person:1.8), (duplicate body parts:1.4), (missing limbs:1.4), (bad hands:1.4)"
        }
    ]
}

CRITICAL: BATCH VALIDATION RULES:
1. Each batch must contain 3-4 sequences
2. Sequences must follow the specified patterns
3. Timing must be consistent within batches
4. Visual continuity must be maintained
5. Story must progress meaningfully

CRITICAL: ERROR PREVENTION:
1. Never skip sequence numbers
2. Never repeat sequence content
3. Never violate timing patterns
4. Never break visual continuity
5. Never use unsupported camera movements

CRITICAL: CAMERA MOVEMENT RULES:
1. Static camera: For establishing shots and emotional moments
2. Pan: For revealing environment or following action
3. Tracking: For following character movement
4. Dolly: For dramatic reveals or emotional emphasis
5. Zoom: For focusing on important details

CRITICAL: LIGHTING CONSISTENCY:
1. Maintain consistent light direction within batches
2. Match lighting to emotional context
3. Use practical light sources when possible
4. Create mood through lighting
5. Progress lighting naturally with story

CRITICAL: COLOR GRADING RULES:
1. Use consistent color palette within batches
2. Match colors to emotional context
3. Progress color grading with story
4. Use color to enhance mood
5. Maintain visual continuity

CRITICAL: SOUND DESIGN RULES:
1. Match music to visual rhythm
2. Use sound to enhance emotion
3. Create atmosphere through sound
4. Progress sound design with story
5. Maintain audio-visual sync"""

app = Flask(__name__)

def call_ollama(prompt: str, system: str = None, temperature: float = 0.7, max_tokens: int = 12000) -> str:
    """Call Ollama API with the given prompt."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        
        # Prepare the payload for Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system,
            "stream": False,  # Disable streaming
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Make the API call
        logger.debug(f"Sending request to Ollama: {payload}")
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            raise Exception(f"Ollama API error: {response.status_code}")
        
        # Extract the generated text from Ollama's response
        response_data = response.json()
        logger.debug(f"Ollama response: {response_data}")
        
        return response_data.get("response", "")
    
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        raise

def parse_json_response(response_text: str) -> Dict:
    """Parse JSON response from model output."""
    try:
        # Debug: Print the full response text
        logger.debug(f"Full response text: {response_text}")
        
        # Try to extract JSON from the response
        # First attempt: Find first { and last }
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed_json = json.loads(json_str)
            logger.debug(f"Successfully parsed JSON: {parsed_json}")
            return parsed_json
        else:
            raise ValueError("No JSON object found in response")
    
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Error occurred at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
        raise

def generate_story_chunk(prompt, chunk_number, total_chunks, previous_character=None, previous_sequence=None, genre=None):
    """Generate a chunk of the story with continuity from previous chunks."""
    
    # Define which part of the story this chunk represents based on 3-act structure
    story_progress = ""
    if chunk_number == 1:
        story_progress = """
This is ACT 1 (SETUP).
- Establish a compelling character through visual details and environment
- Create a distinctive visual baseline (color palette, lighting style)
- Include a clear inciting incident by sequence 3-4
- End with character making a decision/accepting a challenge
- VISUAL STYLE: Stable compositions, consistent lighting, defined color palette
- CAMERA WORK: Start with establishing shots, transition to medium shots
- PACING: Begin with longer, stable shots (4-6 seconds for b-roll)
- CHARACTER VISUALS: Introduce character in their normal element
- SHOT PATTERNS: Use "wide -> wide -> wide" pattern for establishing shots
- TIMING: Use consistent 2.5s durations for wide shots to establish rhythm

B-ROLL GUIDELINES FOR ACT 1:
- Use longer establishing shots (4-6 seconds)
- Focus on environmental scale and grandeur
- Establish location's distinctive features
- Create strong sense of place and atmosphere
- SHOT PATTERN: "wide -> wide -> wide" for establishing location
"""
    elif chunk_number == total_chunks:
        story_progress = """
This is ACT 3 (RESOLUTION).
- Begin with character finding new determination after lowest point
- Build to a visually striking climactic confrontation
- Show clear visual transformation from beginning state
- Include visual callback to opening sequence but with meaningful differences
- VISUAL STYLE: Return to stability but with transformation, evolved color palette
- CAMERA WORK: Dynamic shots for climax, then settle into stable framing
- PACING: Intense during climax, gradually relaxing for resolution
- CHARACTER VISUALS: Show visual transformation through posture, expression, and appearance
- SHOT PATTERNS: Use "wide -> close-up -> wide" pattern for emotional emphasis
- TIMING: Use decreasing rhythm (2.9s -> 1.9s -> 1.0s) for urgency in climax
"""
    else:
        # Calculate if we're in early or late Act 2
        if chunk_number <= total_chunks // 2:
            story_progress = """
This is early ACT 2 (CONFRONTATION-RISING).
- Present initial obstacles and complications
- Build tension through increasingly dynamic visuals
- Include a major revelation or turning point (midpoint)
- Show character struggling but initially coping
- VISUAL STYLE: More dynamic compositions, intensifying colors, increased contrast
- CAMERA WORK: More movement, varied angles, increasing close-ups
- PACING: More motion, increased visual energy
- CHARACTER VISUALS: Show initial stress through subtle visual changes
- SHOT PATTERNS: Use "wide -> medium -> wide" pattern for character focus
- TIMING: Use building rhythm (2.3s -> 2.4s -> 2.5s) to create tension

B-ROLL GUIDELINES FOR EARLY ACT 2:
- Show environment's challenges and obstacles
- Use weather and lighting to build tension
- Create visual metaphors through environment
- SHOT PATTERN: "wide -> detail -> wide" for revealing threats
"""
        else:
            story_progress = """
This is late ACT 2 (CONFRONTATION-FALLING).
- Increase stakes and obstacles to seemingly insurmountable levels
- Create false victory followed by major setback
- End with character at their lowest point/dark night of the soul
- VISUAL STYLE: Most unstable compositions, extreme visual style
- CAMERA WORK: Unstable framing, extreme angles, disorienting movement
- PACING: Varied rhythms building to crisis
- CHARACTER VISUALS: Show maximum visual distress and deterioration
- SHOT PATTERNS: Use "medium -> close-up -> medium" pattern for character focus
- TIMING: Use contrasting rhythm (7s -> 3s -> 2s) for dramatic emphasis

B-ROLL GUIDELINES FOR LATE ACT 2:
- Show environment at its most threatening
- Use extreme weather or conditions
- Create claustrophobic or overwhelming spaces
- SHOT PATTERN: "wide -> close -> extreme wide" for emotional impact
"""
    
    # Customize for genre if provided
    genre_guidance = ""
    if genre:
        if genre.lower() == "noir":
            genre_guidance = """
NOIR VISUAL ELEMENTS:
- Use high contrast lighting with dramatic shadows
- Create rain-soaked environments with reflective surfaces
- Employ dutch/canted angles during moments of psychological stress
- Use neon lighting for color accents in dark environments
- Frame character through doorways/windows to suggest entrapment
- SHOT PATTERNS: Use "wide -> close-up -> wide" for mystery moments
- TIMING: Use longer durations (4-5s) for contemplative shots
"""
        elif genre.lower() == "sci-fi":
            genre_guidance = """
SCI-FI VISUAL ELEMENTS:
- Create contrast between advanced technology and human elements
- Use cool color palettes (blues, teals) with strategic accent colors
- Employ reflective surfaces and lighting through geometric patterns
- Frame human elements against vast technological/space backgrounds
- Use lens flares and volumetric lighting for technological elements
- SHOT PATTERNS: Use "wide -> medium -> wide" for technology reveals
- TIMING: Use consistent 2.5s durations for wide shots of technology
"""
        elif genre.lower() == "horror":
            genre_guidance = """
HORROR VISUAL ELEMENTS:
- Obscure key elements in shadow or partial lighting
- Use negative space to create tension and anticipation
- Employ unsettling compositions with subject in vulnerable positions
- Create visual intrusions/violations of normal space
- Use extreme close-ups of tense physical reactions
- SHOT PATTERNS: Use "wide -> close-up -> wide" for jump scares
- TIMING: Use decreasing rhythm (2.9s -> 1.9s -> 1.0s) for tension
"""
        elif genre.lower() == "romance":
            genre_guidance = """
ROMANCE VISUAL ELEMENTS:
- Use soft, flattering lighting with warm color palettes
- Create intimate framing with shallow depth of field
- Employ mirror/reflection shots for self-realization moments
- Use nature elements to reflect emotional states
- Create visual bridges between characters (similar colors, compositional elements)
- SHOT PATTERNS: Use "medium -> close-up -> medium" for emotional moments
- TIMING: Use longer durations (6-7s) for medium shots of characters
"""
        elif genre.lower() == "action":
            genre_guidance = """
ACTION VISUAL ELEMENTS:
- Use dynamic camera movements that match action intensity
- Create strong directional lighting with high contrast
- Employ low angles to emphasize power and threat
- Use quick cutting between wide and close shots
- Include environment interactions (debris, impacts, reactions)
- SHOT PATTERNS: Use "wide -> wide -> wide" for action sequences
- TIMING: Use shorter durations (2.0-2.5s) for fast-paced action
"""
    
    chunk_prompt = f"""Create a story about: {prompt}

This is chunk {chunk_number} of {total_chunks}.
{story_progress}
{genre_guidance}

Generate exactly 8-10 sequences that continue the story naturally.
IMPORTANT: Each clip_action MUST be context-aware, referencing elements that exist in the scene and matching the emotional context.

SHOT TYPE AND TIMING GUIDELINES:
1. Wide shots: 2.5-4.5 seconds (most common)
2. Medium shots: 6.0-7.0 seconds (longer, more deliberate)
3. Close-ups: 2.0-3.0 seconds (intimate, focused)
4. Character scenes: 4.0-5.0 seconds
5. B-roll scenes: 3.0-4.0 seconds

COMMON SHOT PATTERNS:
1. "wide -> wide -> wide" (most common)
2. "wide -> medium -> wide" (second most common)
3. "wide -> wide -> medium" (third most common)
4. "medium -> wide -> wide" (fourth most common)
5. "medium -> wide -> medium" (fifth most common)
6. "wide -> close-up -> wide" (for emotional emphasis)
7. "medium -> close-up -> medium" (for character focus)

TIMING PATTERNS:
1. Consistent timing: "wide 2.5s -> wide 2.5s -> wide 2.5s"
2. Gradual timing: "wide 2.3s -> wide 2.4s -> wide 2.5s"
3. Contrasting timing: "wide 7s -> medium 3s -> wide 2s"
4. Character focus: "medium 6s -> close-up 2s -> medium 5s"
5. Emotional emphasis: "wide 4s -> close-up 2s -> wide 3s"

CLOSE-UP USAGE:
1. Emotional moments: 2.0-3.0 seconds
2. Detail emphasis: 1.5-2.5 seconds
3. Use for character reactions and important details
4. Often paired with internal dialogue
5. Creates visual variety and maintains viewer interest

VISUAL STORYTELLING REQUIREMENTS:
1. Create meaningful visual progression - not just random shots
2. For character shots: Use only supported character animations based on character traits
3. For b-roll shots: Use only supported environmental animations based on scene type
4. Use camera techniques that enhance emotional content:
   - Static shots for tension/focus
   - Moving shots for revelation/transformation
   - Low angles for power/threat
   - High angles for vulnerability/perspective
5. Create visual continuity between sequences
6. No character names in voice narration (first-person internal monologue only)
7. Every clip_action must reference actual elements in the scene and match the emotional context
8. Use atmosphere descriptors to create specific mood and color palettes
"""
    
    if previous_character:
        chunk_prompt += f"\nPrevious character details: {json.dumps(previous_character)}"
    if previous_sequence:
        chunk_prompt += f"\nLast sequence: {json.dumps(previous_sequence)}\n"
        chunk_prompt += f"\nContinue the visual style established in previous sequences while evolving it to match this part of the story."
    
    # For Ollama, we'll combine the system prompt with our user prompt
    full_prompt = f"{system_prompt}\n\n{chunk_prompt}"
    
    # Call Ollama
    response_text = call_ollama(
        prompt=chunk_prompt,
        system=system_prompt
    )
    
    # Parse the response
    try:
        return parse_json_response(response_text)
    except Exception as e:
        logger.error(f"Failed to parse response: {e}")
        # Return a minimal valid structure as fallback
        return {
            "character": {
                "base_traits": "(mid-30s person:1.4)",
                "facial_features": "(expressive eyes:1.3)",
                "distinctive_features": "(unique feature:1.4)",
                "clothing": "(appropriate attire:1.2)"
            },
            "music_score": {
                "type": "ambient",
                "style": "atmospheric",
                "tempo": "moderate",
                "instrumentation": "subtle mix"
            },
            "sequence": [
                {
                    "sequence_number": 1,
                    "clip_duration": 3.0,
                    "clip_action": "static camera, subtle movement",
                    "voice_narration": "...",
                    "type": "b-roll",
                    "environment": "ESTABLISHING SHOT - LOCATION - TIME",
                    "atmosphere": "(high quality:1.4), (cinematic:1.3)",
                    "negative_prompt": "(low quality:1.4), (blurry:1.2)"
                }
            ]
        }

@app.route('/generate-cinematic-story', methods=['POST'])
def generate_cinematic_story():
    try:
        # Get request data
        data = request.get_json(force=True)
        logger.debug(f"Received request data: {data}")
        
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Please provide a prompt', 'status': 'error'}), 400
        
        # Extract parameters
        prompt = data.get('prompt')
        genre = data.get('genre')
        num_sequences = data.get('num_sequences', 12)  # Default to 12 sequences for Mistral (reduced from 25)
        
        # Calculate number of chunks needed based on requested sequence count
        # Each chunk will generate ~4-6 sequences with Mistral
        sequences_per_chunk = 4
        total_chunks = max(3, math.ceil(num_sequences / sequences_per_chunk))
        
        # Ensure we have at least 3 chunks for proper 3-act structure
        if total_chunks < 3:
            total_chunks = 3
        
        # Generate first chunk (Act 1)
        first_chunk = generate_story_chunk(
            prompt, 
            1, 
            total_chunks,
            genre=genre
        )
        final_story = first_chunk
        
        # Generate subsequent chunks with continuity
        for chunk_num in range(2, total_chunks + 1):
            previous_sequence = final_story['sequence'][-1]
            chunk = generate_story_chunk(
                prompt, 
                chunk_num, 
                total_chunks,
                previous_character=final_story['character'],
                previous_sequence=previous_sequence,
                genre=genre
            )
            
            # Adjust sequence numbers for continuity
            start_seq_num = len(final_story['sequence']) + 1
            for i, seq in enumerate(chunk['sequence']):
                seq['sequence_number'] = start_seq_num + i
            
            # Append new sequences while maintaining character consistency
            final_story['sequence'].extend(chunk['sequence'])
            
            # Log progress
            logger.debug(f"Generated chunk {chunk_num} with {len(chunk['sequence'])} sequences")
        
        # Ensure we have exactly the requested number of sequences
        if len(final_story['sequence']) > num_sequences:
            final_story['sequence'] = final_story['sequence'][:num_sequences]
        
        # Log final story length
        logger.debug(f"Final story contains {len(final_story['sequence'])} sequences")
        
        return jsonify(final_story)
            
    except Exception as e:
        logger.error(f"Error generating cinematic story: {str(e)}")
        return jsonify({
            'error': f"Error: {str(e)}",
            'status': 'error'
        }), 500

# Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Check if Ollama API is available
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        
        if response.status_code == 200:
            return jsonify({
                'status': 'healthy',
                'ollama_status': 'connected',
                'available_models': response.json()
            })
        else:
            return jsonify({
                'status': 'degraded',
                'ollama_status': 'error',
                'error': f'Ollama API returned status code {response.status_code}'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'degraded',
            'ollama_status': 'disconnected',
            'error': f'Cannot connect to Ollama API: {str(e)}'
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True)