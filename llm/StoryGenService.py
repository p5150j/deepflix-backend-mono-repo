from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import json
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any
import math
import time
import requests

# Set up logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('anthropic_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Debug: Check if API key is loaded
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    logger.error("ANTHROPIC_API_KEY not found in environment variables")
else:
    logger.debug("ANTHROPIC_API_KEY loaded successfully")

# System prompt for Claude
system_prompt = """IMPORTANT: Return ONLY the JSON structure below. Do not add any explanatory text, introductions, or additional formatting before or after the JSON. The response must start with { and end with }.

Return this exact JSON structure with your story content. Do not add any other text or formatting before or after the JSON. The response must start with { and end with }:
example json (this is just an example, do not follow values exactly):
{
    "movie_info": {
        "genre": "noir",
        "title": "The Dark Side of the City",
        "description": "A private investigator is hired to find a missing woman who may be involved in a dangerous criminal organization. As he delves deeper into the case, he discovers a web of secrets and lies that threaten to destroy everything he holds dear.",
        "release_year": 2024,
        "director": "John Doe",
        "rating": 7.5
    },
    "character": {
        "base_traits": "young 18 year old female, slender frame, fair complexion",
        "facial_features": "defined features, slightly parted lips, expressive eyes, high contrast facial structure",
        "distinctive_features": "white hair, multiple facial piercings, contrasting against skin tone and chest tattoos",
        "clothing": "minimal visible clothing, possibly dark casual wear"
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
            "clip_action": "dust particles catching golden light as they drift upward, creating delicate patterns of illumination across rusted metal surfaces",
            "voice_narration": "...",
            "type": "b-roll",
            "environment": "ESTABLISHING SHOT - EYE LEVEL - RULE OF THIRDS - EXT. ABANDONED WAREHOUSE WITH BROKEN WINDOWS AND RUSTED METAL DOORS - DAY - DUST PARTICLES FLOATING IN SUNBEAMS",
            "atmosphere": "8k uhd, photorealistic, natural sunlight streaming through broken windows, dramatic shadows cast by debris, high contrast between light beams and dark corners, studio lighting quality, sharp details on textured surfaces, cinematic color grading with warm highlights and cool shadows"
        },
        {
            "sequence_number": 2,
            "clip_duration": 3.0625,
            "clip_action": "fabric rippling delicately as breath escapes, shadows shifting subtly across exposed brick wall, dust particles catching light around face",
            "voice_narration": "It has to be here somewhere...",
            "type": "character",
            "pose": "[previous character traits], face turned slightly toward light source, chin slightly lowered, lips parted subtly, eyes catching highlight from sunbeam",
            "environment": "CLOSE UP - EYE LEVEL - PORTRAIT FRAMING - INT. WAREHOUSE CORNER WITH EXPOSED BRICK WALL AND SINGLE SUNBEAM - DAY - DUST PARTICLES CATCHING LIGHT",
            "atmosphere": "8k uhd, photorealistic, natural sunlight beam creating dramatic rim lighting, high contrast ratio between illuminated face and dark background, warm highlights on skin catching dust particles, studio portrait quality with shallow depth of field, sharp details on facial features, cinematic color grading with golden hour tones"
        }
    ]
}

MOVIE_INFO REQUIREMENTS:
1. genre: Must match the requested genre exactly (e.g., "noir", "sci-fi", "horror", etc.)
2. title: Create a compelling, genre-appropriate title that reflects the story's theme
3. description: Write a 2-3 sentence synopsis that captures the main plot and tone
4. release_year: Set to current year (2025)
5. director: Generate a realistic director name
6. rating: Provide a realistic rating between 7.0 and 9.5

Guidelines for Parameter Generation:

Character Data:
1. base_traits:
   - Physical Attributes (Required):
     * Age range or specific age
     * Ethnicity/background
     * Gender
     * Body type and build
     * Height and proportions
   
   - Format: "age, ethnicity, gender, body type, build"
   - Examples:
     * "young female, slender frame, fair complexion"
     * "middle-aged male, athletic build, weathered features"
     * "elderly woman, petite frame, graceful posture"

2. facial_features:
   - Eye Details (Required):
     * Shape and color
     * Expression quality
     * Eye spacing and position
   
   - Facial Structure (Required):
     * Bone structure
     * Feature placement
     * Overall symmetry
   
   - Skin Quality (Required):
     * Texture and tone
     * Notable features
     * Age indicators
   
   Format: Combine elements with commas
   Examples:
   - "defined features, slightly parted lips, expressive eyes, high contrast facial structure"
   - "strong jawline, deep-set eyes, weathered skin, prominent cheekbones"
   - "delicate features, wide-set eyes, smooth complexion, gentle facial structure"

3. clothing:
   - Primary Garments (Required):
     * Material and texture
     * Style and cut
     * Color and pattern
   
   - Fit and Condition (Required):
     * How clothing sits on body
     * Wear and tear
     * Movement quality
   
   - Accessories (Optional):
     * Jewelry and adornments
     * Practical items
     * Character-defining pieces
   
   Format: "material style condition, accessories"
   Examples:
   - "minimal visible clothing, possibly dark casual wear"
   - "worn leather jacket, fitted black jeans, scuffed boots"
   - "flowing silk dress, delicate silver jewelry, practical belt"

4. distinctive_features:
   - Unique Elements (Required):
     * Unusual physical traits
     * Notable markings
     * Distinctive characteristics
   
   - Hair Details (Required):
     * Style and cut
     * Color and texture
     * Movement quality
   
   - Special Features (Optional):
     * Piercings, Tattoos or modifications
     * Character-defining elements
     * Memorable details
   
   Format: "unique elements, hair details, special features"
   Examples:
   - "white hair, multiple facial piercings, contrasting against skin tone"
   - "vibrant red hair, geometric tattoos, silver ear cuffs"
   - "silver-streaked hair, ancient scar, glowing eyes"

Scene Data:
1. pose:
   - Base Posture (Required):
     * Standing, sitting, kneeling, etc.
     * Include direction (e.g., "turned slightly toward light")
     * Specify stance (e.g., "tense posture", "relaxed stance")
   
   - Facial Expression (Required):
     * Eye direction and focus
     * Mouth position (e.g., "lips parted subtly")
     * Overall expression (e.g., "focused expression")
   
   - Hand/Body Position (Required):
     * Specific gestures
     * Body orientation
     * Movement state
   
   - Light Interaction (Required):
     * How pose interacts with lighting
     * Shadow placement
     * Highlight positions
   
   Format: "[previous character traits], base posture, facial expression, hand/body position, light interaction"

   Examples:
   - "[previous character traits], standing at workshop doorway, tense posture, face turned slightly toward light source, chin slightly lowered, lips parted subtly, eyes catching highlight from sunbeam"
   - "[previous character traits], leaning over workbench, focused expression, hands working deliberately, face illuminated by warm studio lights"
   - "[previous character traits], silhouette in doorframe, tense posture, face in shadow, body catching edge light, hands gripping doorframe"

2. environment:
   - Shot Type (Required):
     * ESTABLISHING SHOT: Wide environment views with specific details
     * MEDIUM SHOT: Character interaction spaces with concrete elements
     * CLOSE UP: Emotional moments with specific visual focus
     * EXTREME CLOSE UP: Intense detail shots with precise elements
     * TRACKING SHOT: Dynamic movement spaces with clear paths
   
   - Camera Angle (Required):
     * EYE LEVEL: Standard perspective with specific height reference
     * LOW ANGLE: Looking up at subject with ground reference
     * HIGH ANGLE: Looking down with ceiling/sky reference
     * DUTCH ANGLE: Tilted perspective with specific angle
   
   - Composition (Required):
     * RULE OF THIRDS: Specific element placement
     * CENTERED: Symmetrical arrangement with clear focal point
     * PORTRAIT FRAMING: Character-focused composition with specific positioning
     * LEADING LINES: Clear directional elements with specific paths
   
   - Location Details (Required):
     * INT./EXT.: Interior or exterior with specific space type
     * Specific setting with concrete visual elements:
       - Room type (e.g., "modern kitchen with stainless steel appliances")
       - Architectural features (e.g., "floor-to-ceiling windows")
       - Furniture placement (e.g., "wooden desk against wall")
       - Lighting sources (e.g., "desk lamp casting warm glow")
     * Time of day with specific lighting conditions
     * Weather/conditions with visible effects
   
   Format: "SHOT TYPE - ANGLE - COMPOSITION - SPECIFIC LOCATION WITH VISUAL ELEMENTS - TIME - CONDITIONS"

   Examples:
   - "ESTABLISHING SHOT - EYE LEVEL - RULE OF THIRDS - EXT. MARTIAN RIDGE WITH RED ROCK FORMATIONS AND DUST DEVILS - DAY - DUST STORM WITH VISIBLE PARTICLES"
   - "MEDIUM SHOT - LOW ANGLE - CENTERED - INT. DARK STUDIO WITH EXPOSED BRICK WALL AND SINGLE HANGING LIGHT BULB - NIGHT - FOG WITH VISIBLE LIGHT RAYS"
   - "CLOSE UP - EYE LEVEL - PORTRAIT FRAMING - INT. WORKSHOP WITH CLUTTERED WOODEN BENCH AND SCATTERED TOOLS - DAY - NATURAL LIGHT STREAMING THROUGH DIRTY WINDOWS"

3. atmosphere:
   - Base Quality (Required):
     * "8k uhd, photorealistic, cinematic lighting"
     * "8k uhd, photorealistic, natural lighting"
     * "8k uhd, photorealistic, studio lighting quality"
   
   - Technical Quality (Required):
     * "sharp details, high contrast ratio"
     * "cinematic color grading, professional quality"
     * "studio portrait quality, sharp details"
   
   - Lighting Direction (Required):
     * "natural sunlight, dramatic shadows"
     * "dramatic backlighting, silhouette effect"
     * "soft natural lighting, diffused sunlight"
   
   - Color Palette (Required):
     * "high contrast, dark background, warm highlights"
     * "deep blacks in background, warm highlights on skin"
     * "cool blue tones, warm golden accents"
   
   - Special Effects (Optional):
     * "volumetric lighting, lens flares"
     * "atmospheric haze, light diffusion"
     * "cinematic vignette, color grading"

   Format: Combine elements in this order:
   "base quality, technical quality, lighting direction, color palette, special effects"

   Examples:
   - "8k uhd, photorealistic, natural sunlight, dramatic shadows, high contrast, dark background, studio lighting quality, sharp details, cinematic color grading"
   - "8k uhd, photorealistic, dramatic backlighting, silhouette effect, deep blacks in background, warm highlights on skin, studio portrait quality, sharp details"
   - "8k uhd, photorealistic, soft natural lighting, diffused sunlight, cool blue tones, warm golden accents, cinematic color grading, professional quality"

5. CLIP_ACTION GENERATION GUIDELINES:

   CORE PRINCIPLES:
   - Each clip_action MUST ONLY reference elements visible in the SD3.5 image
   - Be highly detailed in describing the movement, but keep the movement itself simple
   - Focus on rich, cinematic descriptions of basic movements
   - Match the emotional context while staying technically feasible
   - Use professional cinematography terminology for quality

   STRICT PROHIBITIONS:
   - NO referencing elements not visible in the image
   - NO complex or multiple simultaneous movements
   - NO camera movements (CogVideoX handles this separately)
   - NO emotional descriptions without physical movement
   - NO actions that require multiple steps or coordination
   - NO describing multiple people or objects unless explicitly visible
   - NO describing actions that would require complex animation

   CONTEXT AWARENESS:
   For Character Shots:
   - ONLY reference visible character elements from pose field
   - Use rich detail to describe simple movements
   - Example:
     pose: "standing at workshop doorway, tense posture"
     clip_action: "fabric rippling delicately as breath escapes, shadows shifting subtly across features"

   For B-Roll Shots:
   - ONLY reference visible environment elements
   - Use rich detail to describe simple movements
   - Example:
     environment: "ESTABLISHING SHOT - EXT. DESERT - SUNSET - DUST STORM"
     clip_action: "dust particles catching golden light as they drift upward, creating delicate patterns of illumination"

   DETAILED MOVEMENT GUIDELINES:
   1. Character Movements:
      - Rich descriptions of subtle posture shifts
      - Detailed observations of gentle head turns
      - Cinematic descriptions of breathing movements
      - Professional detail of fabric movement
      - Artistic descriptions of simple gestures

   2. Environmental Movements:
      - Detailed observations of particle drift
      - Cinematic descriptions of leaf movement
      - Professional detail of water ripple
      - Artistic descriptions of dust floating
      - Rich detail of smoke curl

   DURATION-BASED COMPLEXITY:
   - 2.0-2.5s: Single movement with rich detail
   - 2.5-3.0s: Two related movements with cinematic detail
   - 3.0-4.0s: Two to three related movements with professional detail
   - 4.0-5.0s: Three to four related movements with artistic detail
   - 5.0-6.0s: Four to five related movements with rich cinematic detail

   VALIDATION CHECKLIST:
   ✓ Does it ONLY reference visible elements?
   ✓ Is the movement simple but described in detail?
   ✓ Does it avoid complex or multiple movements?
   ✓ Is it technically feasible for CogVideoX?
   ✓ Does it match the emotional context?
   ✓ Does it use rich, cinematic language?
   ✓ Does it avoid describing multiple people/objects?
   ✓ Does it avoid complex animation requirements?

   EXAMPLES:
   Good (Detailed but Simple Movements):
   - "fabric rippling delicately as breath escapes, shadows shifting subtly across features"
   - "dust particles catching golden light as they drift upward, creating delicate patterns of illumination"
   - "leaves swaying gently in breeze, dappled light dancing across their surface"
   - "water rippling softly, reflections of sky creating intricate patterns of light"
   - "smoke curling upward slowly, wisps catching the warm glow of sunset"

   Bad (Complex or Invisible Elements):
   - "character performing complex choreography"
   - "multiple elements moving in different directions"
   - "referencing off-screen elements or actions"
   - "emotional descriptions without physical movement"
   - "actions requiring coordination or multiple steps"
   - "multiple people moving through the scene"
   - "complex interactions between objects"
   - "describing elements not visible in the image"

   CORRECTED EXAMPLES:
   Original: "static camera, eyes scanning contact sheet of photographs, fingers tracing lines between images, subtle shift in posture as revelation forms, breath creating slight movement in shoulders"
   Corrected: "fabric rippling delicately as breath escapes, shadows shifting subtly across features, posture adjusting slightly"

   Original: "static camera, industrial workers streaming through concrete passage, faces tired but determined, steam rising from vents creating atmospheric haze, shadows casting patterns across moving figures"
   Corrected: "steam rising slowly from vents, creating delicate patterns of light and shadow across the concrete surface"

6. SHOT PROGRESSION AND TIMING GUIDELINES:

   Shot Progression Guidelines:
   1. Opening Sequence:
      - Start with ESTABLISHING SHOT (wide)
      - Follow with another wide shot
      - Introduce character with MEDIUM SHOT
      - Return to wide shot
      - Use gentle camera movements
   
   2. Common Patterns:
      - "wide -> wide -> wide" (most common)
      - "wide -> medium -> wide" (second most common)
      - "wide -> wide -> medium" (third most common)
      - "medium -> wide -> wide" (fourth most common)
      - "medium -> wide -> medium" (fifth most common)
      - "wide -> close-up -> wide" (for emotional emphasis)
      - "medium -> close-up -> medium" (for character focus)

   Timing Pattern Analysis:
   1. Most Common Timing Patterns:
      - "wide 2.5s -> wide 2.5s -> wide 2.5s"
      - "wide 2.3s -> wide 2.4s -> wide 2.5s"
      - "wide 7s -> medium 3s -> wide 2s"
      - "wide 3s -> wide 3s -> wide 3s"
      - "wide 2s -> wide 2s -> wide 2s"
      - "medium 6s -> close-up 2s -> medium 5s" (for character focus)
      - "wide 4s -> close-up 2s -> wide 3s" (for emotional emphasis)

   2. Timing Pattern Principles:
      - Consistent timing creates rhythm (e.g., three 2.5s shots)
      - Gradual timing changes create flow (e.g., 2.3s -> 2.4s -> 2.5s)
      - Contrasting timing creates emphasis (e.g., 7s -> 3s -> 2s)
      - Shorter shots increase pace and tension
      - Longer shots allow for contemplation and atmosphere
      - Close-ups are typically shorter (2.0-3.0s) to maintain visual energy

   Rhythm Pattern Guidelines:
   1. Consistent Rhythm:
      - Use three similar shots with similar durations (e.g., three 2.5s wide shots)
      - This creates a stable, rhythmic foundation

   2. Contrast Rhythm:
      - Follow a long shot with shorter shots (e.g., 7s -> 3s -> 2s)
      - This creates emphasis and visual interest

   3. Building Rhythm:
      - Gradually increase shot durations (e.g., 2.3s -> 2.4s -> 2.5s)
      - This creates a sense of building tension

   4. Decreasing Rhythm:
      - Gradually decrease shot durations (e.g., 2.9s -> 1.9s -> 1.0s)
      - This creates a sense of urgency or resolution

   5. Shot Type Transitions:
      - Wide -> Medium -> Wide: Creates focus then context
      - Wide -> Wide -> Medium: Builds to a character moment
      - Medium -> Wide -> Wide: Starts with focus, expands to context
      - Wide -> Close-up -> Wide: Creates emotional emphasis
      - Medium -> Close-up -> Medium: Maintains character focus
      - Close-up -> Wide -> Close-up: Creates visual contrast

   Close-up Usage Guidelines:
   1. Emotional Moments:
      - Use close-ups for character reactions and emotional responses
      - Typical duration: 2.0-3.0 seconds
      - Often paired with internal dialogue in voice narration

   2. Detail Emphasis:
      - Use close-ups to highlight important objects or details
      - Typical duration: 1.5-2.5 seconds
      - Often used in mystery or discovery moments

   3. Transitional Close-ups:
      - Use close-ups as transitions between wider shots
      - Creates visual variety and maintains viewer interest
      - Often used in montage sequences

   4. Close-up Patterns:
      - Wide -> Close-up -> Wide: Creates emotional emphasis
      - Medium -> Close-up -> Medium: Maintains character focus
      - Close-up -> Wide -> Close-up: Creates visual contrast
      - Multiple close-ups in sequence: Creates intensity and focus

   5. Close-up Composition:
      - Focus on eyes, hands, or specific facial features
      - Use shallow depth of field for emphasis
      - Consider lighting direction for dramatic effect
      - Match close-up composition to emotional content

   Shot Types:
   - ESTABLISHING SHOT: Wide shots showing environment
   - MEDIUM SHOT: Full body or waist-up shots
   - CLOSE UP: Head and shoulders or closer
   - WIDE SHOT: Full environment with character
   - LOW ANGLE: Looking up at subject
   - HIGH ANGLE: Looking down at subject

   Shot Duration Guidelines:
   1. Shot Types:
      - Wide shots: 2.5-4.5 seconds (most common)
      - Medium shots: 6.0-7.0 seconds (longer, more deliberate)
      - Close-ups: 2.0-3.0 seconds (intimate, focused)
      - Character scenes: 4.0-5.0 seconds
      - B-roll scenes: 3.0-4.0 seconds
      - Pattern: wide 2.5s -> wide 2.5s -> wide 2.5s (most common rhythm)

   Technical Guidelines:
   1. Camera Movement:
      - Start gentle (pans, tilts)
      - Progress to tracking
      - Add dynamic movements for tension
      - Return to gentle for resolution

   2. Lighting Progression:
      - Begin with natural/ambient
      - Add dramatic lighting
      - Use practical sources
      - Create mood through lighting

   3. Shot Duration:
      - Establishing shots: 4.0-6.0 seconds
      - Medium shots: 2.5-3.5 seconds
      - Close-ups: 1.5-2.5 seconds
      - Tracking shots: 3.0-4.0 seconds

   4. Visual Continuity:
      - Maintain consistent color grading
      - Match lighting between shots
      - Keep character appearance consistent
      - Progress environment naturally

   Shot Types and Their Uses:
   1. ESTABLISHING SHOT:
      - Wide shots showing environment
      - Used for scene setting and context
      - Often at the start of a sequence
      - Example: "ESTABLISHING SHOT - low angle - rule of thirds - small midwestern town, dusk, neon signs, fog rolling in"

   2. MEDIUM SHOT:
      - Full body or waist-up shots
      - Used for character action and interaction
      - Good for showing movement and gestures
      - Example: "MEDIUM SHOT - eye level - centered - high school hallway, lockers, scattered papers, flickering lights"

   3. CLOSE UP:
      - Head and shoulders or closer
      - Used for emotional moments and details
      - Good for showing reactions and expressions
      - Example: "CLOSE UP - eye level - rule of thirds - face illuminated by flashlight, black veins in background, sweat dripping"

   4. TRACKING SHOT:
      - Following character movement
      - Used for dynamic scenes and chase sequences
      - Maintains continuous motion
      - Example: "TRACKING SHOT - low angle - rule of thirds - school corridor, emergency lights, papers flying, smoke rising"

   5. AERIAL SHOT:
      - Overhead or elevated perspective
      - Used for establishing scale and scope
      - Good for dramatic reveals
      - Example: "AERIAL SHOT - high angle - centered - small town, spreading darkness, lights going out, storm clouds gathering"

   Visual Storytelling Structure:
   1. Character Consistency:
      - Character traits from the "character" section must be referenced in every character shot's pose
      - Use [previous character traits] to include all character traits in poses
      - Example: "pose": "[previous character traits], (sitting:1.4)"
      - This ensures visual consistency across all character shots

   2. Shot Types and Sequence:
      - "b-roll": Establishing shots and environment details
      - "character": Shots featuring main characters
      - Sequence must follow: Start with b-roll → Introduce character → Mix detail shots → End with b-roll
      - For character shots, always include pose with [previous character traits]
      - For b-roll shots, focus on environment and atmosphere
      - Never use "environment" or "object" as type - only "b-roll" or "character"

   3. Token Management:
      - Positive Prompt: 77 tokens maximum
      - Include all character traits in poses while staying within token limits

   B-Roll Guidelines:
   1. Establishing B-Roll:
      - Wide establishing shots
      - Environment introduction
      - Setting the mood
      - Example: "ESTABLISHING SHOT - small midwestern town, dusk, neon signs"

   2. Environmental B-Roll:
      - Show setting details
      - Create atmosphere
      - Build tension
      - Example: "MEDIUM SHOT - abandoned factory, rusted machinery, broken windows"

   3. Detail B-Roll:
      - Close-up details
      - Important objects
      - Environmental clues
      - Example: "CLOSE UP - old photograph, torn edges, faded colors"

   4. Transition B-Roll:
      - Smooth scene transitions
      - Location changes
      - Time passage
      - Example: "TRACKING SHOT - city streets, changing neighborhoods, evolving architecture"

   5. Mood B-Roll:
      - Emotional atmosphere
      - Symbolic elements
      - Thematic reinforcement
      - Example: "AERIAL SHOT - storm clouds gathering, lightning flashes, city below"

   6. Action B-Roll:
      - Dynamic elements
      - Movement and motion
      - Environmental reactions
      - Example: "TRACKING SHOT - papers flying, debris scattering, chaos unfolding"

   7. Character Context B-Roll:
      - Character environment
      - Personal space
      - Emotional setting
      - Example: "MEDIUM SHOT - messy bedroom, scattered belongings, personal items"

   8. Climactic B-Roll:
      - Dramatic reveals
      - Plot points
      - Story moments
      - Example: "ESTABLISHING SHOT - massive explosion, debris flying, smoke rising"

   9. Resolution B-Roll:
      - Story conclusion
      - Aftermath
      - New beginning
      - Example: "AERIAL SHOT - sunrise over city, smoke clearing, hope emerging"

   10. B-Roll to Character Ratio:
       - Maintain 70% b-roll, 30% character shots
       - Use b-roll for story progression
       - Save character shots for key moments
       - Build tension through b-roll
       - Create atmosphere with b-roll
       - Use b-roll for transitions
       - Show environment through b-roll
       - Build story through b-roll
       - Create mood with b-roll
       - Use b-roll for symbolism

   11. B-Roll Progression:
       - Start with establishing shots
       - Build environment gradually
       - Show details progressively
       - Create tension through b-roll
       - Use b-roll for transitions
       - Build to climactic moments
       - Show resolution through b-roll
       - Maintain visual continuity
       - Create emotional impact
       - Build story through b-roll

   12. B-Roll Technical Requirements:
       - Match environment description
       - Follow lighting progression
       - Maintain visual consistency
       - Use appropriate shot types
       - Consider camera movement
       - Match atmosphere settings
       - Follow duration guidelines
       - Maintain quality standards
       - Use appropriate effects
       - Follow cinematic rules

   13. B-Roll Examples:
       - Establishing: "ESTABLISHING SHOT - low angle - rule of thirds - ancient castle, stormy night, lightning flashes, fog rolling in"
       - Environmental: "MEDIUM SHOT - eye level - centered - misty forest, twisted trees, hanging moss, dappled sunlight"
       - Detail: "CLOSE UP - eye level - rule of thirds - old key, rusted metal, intricate details, cobwebs"
       - Transition: "TRACKING SHOT - low angle - rule of thirds - changing seasons, leaves falling, snow beginning, wind blowing"
       - Mood: "AERIAL SHOT - high angle - centered - dark clouds, rain falling, city lights below, lightning in distance"
       - Action: "TRACKING SHOT - low angle - rule of thirds - papers flying, debris scattering, chaos unfolding, smoke rising"
       - Character Context: "MEDIUM SHOT - eye level - centered - messy office, scattered papers, personal items, dim lighting"
       - Climactic: "ESTABLISHING SHOT - low angle - rule of thirds - massive explosion, debris flying, smoke rising, fire spreading"
       - Resolution: "AERIAL SHOT - high angle - centered - sunrise over city, smoke clearing, hope emerging, birds flying"

   14. B-Roll Quality Control:
       - Check environment match
       - Verify lighting consistency
       - Ensure visual continuity
       - Validate shot types
       - Confirm camera movement
       - Check atmosphere settings
       - Verify duration
       - Validate quality
       - Check effects
       - Confirm cinematic rules

   15. B-Roll Best Practices:
       - Start wide, then detail
       - Build environment gradually
       - Show details progressively
       - Create tension through b-roll
       - Use b-roll for transitions
       - Build to climactic moments
       - Show resolution through b-roll
       - Maintain visual continuity
       - Create emotional impact
       - Build story through b-roll

   Voice Narration Guidelines:
   1. Cinematic Storytelling Priority:
      - Visual storytelling should drive the narrative
      - Narration should complement visuals, not replace them
      - Use silence ("...") to let visuals breathe and create mood
      - Follow the "show, don't tell" principle of cinema

   2. Internal Dialogue Rules:
      - Use first-person internal thoughts only
      - Keep internal dialogue brief and impactful
      - Internal dialogue should reveal character's emotional state
      - Avoid describing what's visually obvious
      - Use internal dialogue for subtext and deeper meaning

   3. Narration Distribution:
      - Use "..." for establishing shots (let visuals set the scene)
      - Use "..." for action sequences (let visuals drive the action)
      - Use "..." for emotional moments (let visuals convey emotion)
      - Include internal dialogue for key decisions or revelations
      - Include internal dialogue for character's private thoughts

   4. Duration Guidelines:
      - Internal dialogue should be approximately 70% of clip_duration
      - For example, a 3-second clip should have dialogue that takes about 2 seconds to speak
      - Keep internal dialogue short for quick cuts (1-2 seconds)
      - Allow longer internal dialogue for contemplative moments (3-4 seconds)

   5. Cinematic Examples:
      - ESTABLISHING SHOT: "..." (let the environment tell the story)
      - ACTION SEQUENCE: "..." (let the action speak for itself)
      - EMOTIONAL MOMENT: "..." (let the visuals convey emotion)
      - KEY DECISION: Brief internal dialogue (reveal character's choice)
      - REVELATION: Brief internal dialogue (reveal character's realization)

   6. When to Use Internal Dialogue:
      - Character making a significant decision
      - Character experiencing a revelation
      - Character's private thoughts that can't be shown visually
      - Character's emotional state that needs verbal expression
      - Character's interpretation of events that adds depth

   7. When to Use Silence ("..."):
      - Establishing shots and scene setting
      - Action sequences and movement
      - Emotional moments and reactions
      - Visual storytelling sequences
      - Transitions between scenes
      - When visuals alone tell the story effectively

   8. Voice Narration Duration Rules:
      - Internal dialogue MUST be shorter than clip_duration
      - Calculate approximate spoken duration based on word count:
        * Average speaking rate: 2.5 words per second
        * Add 0.5 seconds buffer for natural pauses
      - STRICT WORD COUNT LIMITS:
        * 2-second clip: Maximum 3 words
        * 3-second clip: Maximum 5 words
        * 4-second clip: Maximum 7 words
        * 5-second clip: Maximum 9 words
        * 6-second clip: Maximum 11 words
      - If narration exceeds these limits:
        * ALWAYS shorten the narration to fit
        * NEVER split into multiple clips
        * NEVER increase clip_duration
      - Examples of valid dialogue lengths:
        * 2s clip: "What is that?"
        * 3s clip: "Something's wrong here"
        * 4s clip: "I have to find it now"
        * 5s clip: "This can't be happening to us"
        * 6s clip: "I need to stop this before it's too late"

   9. Duration Validation Examples:
      - ESTABLISHING SHOT (5s): "..." (silence)
      - QUICK REACTION (2s): "What is that?" (3 words = ~1.2s)
      - EMOTIONAL MOMENT (3s): "..." (silence)
      - KEY DECISION (4s): "I have to try" (4 words = ~1.6s)
      - REVELATION (5s): "This changes everything" (3 words = ~1.2s)

   10. Duration Guidelines by Shot Type:
       - ESTABLISHING SHOT (4-6s): "..." (silence)
       - MEDIUM SHOT (3-4s): Brief internal dialogue (3-5 words)
       - CLOSE UP (2-3s): Very brief internal dialogue (2-3 words)
       - TRACKING SHOT (3-4s): Brief internal dialogue (3-5 words)
       - AERIAL SHOT (4-5s): "..." (silence)

Music Score Guidelines:
1. Score Type Selection:
   - Analyze story genre, mood, and setting
   - Consider character's emotional journey
   - Match score style to visual atmosphere
   - Ensure consistency throughout sequences

2. Style Categories:
   - Ambient: Atmospheric, textural, mood-setting
   - Orchestral: Traditional film score with full orchestra
   - Electronic: Modern, synthetic, digital
   - Hybrid: Combination of acoustic and electronic
   - Period: Historically accurate instrumentation
   - Experimental: Avant-garde, unconventional

3. Tempo Guidelines:
   - Match pacing to story beats
   - Consider clip durations
   - Build tension gradually
   - Allow for emotional moments
   - Support action sequences

4. Instrumentation Rules:
   - Choose instruments that match setting
   - Consider cultural context
   - Balance traditional and modern elements
   - Include both melodic and textural elements
   - Ensure variety in sound palette

5. Genre-Specific Examples:
   - Sci-Fi: "Atmospheric wave synths with reverb-drenched pads and cyberpunk arpeggiators"
   - Western: "Latin-infused guitar interplay with desert atmospherics and minimal percussion"
   - Fantasy: "Ethereal bell textures with ancient instruments and ambient trap undercurrents"
   - Noir: "Darkwave synthesizers with brooding post-punk guitars and melancholic piano motifs"
   - Cyberpunk: "Industrial rhythms with chillwave textures and futuristic techno elements"
   - Romance: "Emotional lo-fi piano with dreamy guitar samples and gentle wave atmospherics"
   - Horror: "Distorted wave bass with dissonant string glitches and mechanical percussion"
   - Space Opera: "Cosmic ambient textures with reverberant lap steel and spatial percussion"
   - Historical: "Authentic instruments processed through modern wave production techniques"
   - Action: "Driving trap percussion with hard-hitting 808s and tense synth stabs"
   - Indie: "Lo-fi guitar textures with emo trap beats and nostalgic analog synths"
   - Superhero: "Bold brass themes with wave-influenced electronic production and melodic bass"

6. Score Structure:
   - Opening: Establish main themes and mood
   - Development: Build complexity and tension
   - Climax: Peak emotional and musical intensity
   - Resolution: Return to themes with closure
   - Transitions: Smooth movement between scenes

7. Emotional Mapping:
   - Joy: Bright, major key, uplifting melodies
   - Sadness: Minor key, slow tempo, sparse arrangement
   - Tension: Dissonance, building rhythms, suspense
   - Action: Fast tempo, strong percussion, driving bass
   - Mystery: Ambiguous harmony, unusual timbres
   - Romance: Warm pads, gentle melodies, intimate arrangement

8. Technical Considerations:
   - Ensure score supports dialogue
   - Allow space for sound effects
   - Consider mix levels
   - Plan for dynamic range
   - Account for scene transitions

9. Score Integration:
   - Match visual pacing
   - Support story beats
   - Enhance emotional moments
   - Create atmosphere
   - Maintain consistency

10. Common Mistakes to Avoid:
    - Overwhelming dialogue
    - Inconsistent style
    - Mismatched tempo
    - Poor transitions
    - Generic choices
    - Ignoring cultural context
    - Lack of thematic development
    - Poor dynamic range
    - Missing emotional support
    - Inappropriate instrumentation
   
"""

app = Flask(__name__)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

def parse_json_response(response_text: str) -> Dict:
    """Parse JSON response using json module."""
    try:
        # Debug: Print the full response text
        logger.debug(f"Full response text: {response_text}")
        
        # Parse the JSON directly
        parsed_json = json.loads(response_text)
        logger.debug(f"Successfully parsed JSON: {parsed_json}")
        
        return parsed_json
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Error occurred at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
        raise

def generate_story_chunk(client, prompt, chunk_number, total_chunks, previous_character=None, previous_sequence=None, genre=None):
    """Generate a chunk of the story with continuity from previous chunks."""
    
    # Define which part of the story this chunk represents based on 3-act structure
    story_progress = ""
    if chunk_number == 1:
        story_progress = """
This is ACT 1 (SETUP).
- Establish a compelling character through professional visual details and environment
- Create a distinctive visual baseline (professional color palette, cinematic lighting style)
- Include a clear inciting incident by sequence 3-4
- End with character making a decision/accepting a challenge
- VISUAL STYLE: Professional compositions with rule of thirds, cinematic lighting with dramatic shadows, defined color palette with rich contrast
- CAMERA WORK: Start with professional establishing shots, transition to medium shots with balanced composition
- PACING: Begin with longer, stable shots (4-6 seconds for b-roll)
- CHARACTER VISUALS: Introduce character in their normal element with professional portrait lighting
- SHOT PATTERNS: Use "wide -> wide -> wide" pattern for establishing shots with dynamic framing
- TIMING: Use consistent 2.5s durations for wide shots to establish rhythm

B-ROLL GUIDELINES FOR ACT 1:
- Use longer establishing shots (4-6 seconds) with professional composition
- Focus on environmental scale and grandeur with cinematic framing
- Establish location's distinctive features with professional lighting
- Create strong sense of place and atmosphere with rich visual detail
- SHOT PATTERN: "wide -> wide -> wide" for establishing location with professional framing
"""
    elif chunk_number == total_chunks:
        story_progress = """
This is ACT 3 (RESOLUTION).
- Begin with character finding new determination after lowest point
- Build to a visually striking climactic confrontation with professional cinematography
- Show clear visual transformation from beginning state with cinematic lighting
- Include visual callback to opening sequence but with meaningful differences
- VISUAL STYLE: Return to stability with professional transformation, evolved color palette with cinematic grading
- CAMERA WORK: Dynamic shots for climax with professional tracking, then settle into stable framing with rule of thirds
- PACING: Intense during climax, gradually relaxing for resolution
- CHARACTER VISUALS: Show visual transformation through professional lighting and expression changes
- SHOT PATTERNS: Use "wide -> close-up -> wide" pattern with professional composition
- TIMING: Use decreasing rhythm (2.9s -> 1.9s -> 1.0s) for urgency in climax
"""
    else:
        # Calculate if we're in early or late Act 2
        if chunk_number <= total_chunks // 2:
            story_progress = """
This is early ACT 2 (CONFRONTATION-RISING).
- Present initial obstacles and complications
- Build tension through increasingly dynamic visuals with professional cinematography
- Include a major revelation or turning point (midpoint)
- Show character struggling but initially coping
- VISUAL STYLE: Dynamic compositions with professional depth of field, intensifying colors with cinematic grading, increased contrast with dramatic shadows
- CAMERA WORK: More movement with smooth tracking, varied angles with professional framing, increasing close-ups with shallow depth of field
- PACING: More motion, increased visual energy
- CHARACTER VISUALS: Show initial stress through professional lighting changes and subtle expressions
- SHOT PATTERNS: Use "wide -> medium -> wide" pattern with professional composition
- TIMING: Use building rhythm (2.3s -> 2.4s -> 2.5s) to create tension

B-ROLL GUIDELINES FOR EARLY ACT 2:
- Show environment's challenges and obstacles with professional framing
- Use weather and lighting to build tension with cinematic effects
- Create visual metaphors through environment with professional composition
- SHOT PATTERN: "wide -> detail -> wide" for revealing threats with professional framing
"""
        else:
            story_progress = """
This is late ACT 2 (CONFRONTATION-FALLING).
- Increase stakes and obstacles to seemingly insurmountable levels
- Create false victory followed by major setback
- End with character at their lowest point/dark night of the soul
- VISUAL STYLE: Most unstable compositions with professional cinematography, extreme visual style with cinematic grading
- CAMERA WORK: Unstable framing with professional tracking, extreme angles with balanced composition, disorienting movement with smooth transitions
- PACING: Varied rhythms building to crisis
- CHARACTER VISUALS: Show maximum visual distress through professional lighting and expression changes
- SHOT PATTERNS: Use "medium -> close-up -> medium" pattern with professional composition
- TIMING: Use contrasting rhythm (7s -> 3s -> 2s) for dramatic emphasis

B-ROLL GUIDELINES FOR LATE ACT 2:
- Show environment at its most threatening with professional framing
- Use extreme weather or conditions with cinematic effects
- Create claustrophobic or overwhelming spaces with professional composition
- SHOT PATTERN: "wide -> close -> extreme wide" for emotional impact with professional framing
"""
    
    # Customize for genre if provided
    genre_guidance = ""
    if genre:
        genre = genre.lower()
        if genre == "noir":
            genre_guidance = """
NOIR VISUAL ELEMENTS:
- High contrast lighting with professional chiaroscuro
- Rain-soaked environments with professional reflections
- Dutch angles with professional composition
- Neon lighting with professional color grading
- Framing through doorways with professional depth of field
- SHOT PATTERNS: Use "wide -> close-up -> wide" for mystery moments
- TIMING: Longer durations (4-5s) for contemplative shots
- MUSIC SCORE: Darkwave synthesizers with brooding post-punk guitars and melancholic piano motifs
"""
        elif genre == "sci-fi":
            genre_guidance = """
SCI-FI VISUAL ELEMENTS:
- Contrast with professional lighting design
- Cool color palettes with professional grading
- Reflective surfaces with professional lighting
- Framing against backgrounds with professional composition
- Lens flares with professional effects
- SHOT PATTERNS: Use "wide -> medium -> wide" for technology reveals
- TIMING: Consistent 2.5s durations for wide shots of technology
- MUSIC SCORE: Atmospheric wave synths with reverb-drenched pads and cyberpunk arpeggiators
"""
        elif genre == "horror":
            genre_guidance = """
HORROR VISUAL ELEMENTS:
- Obscured key elements with professional shadow work
- Negative space with professional composition
- Unsettling compositions with professional framing
- Visual intrusions with professional effects
- Extreme close-ups with professional lighting
- SHOT PATTERNS: Use "wide -> close-up -> wide" for jump scares
- TIMING: Decreasing rhythm (2.9s -> 1.9s -> 1.0s) for tension
- MUSIC SCORE: Distorted wave bass with dissonant string glitches and mechanical percussion
"""
        elif genre == "romance":
            genre_guidance = """
ROMANCE VISUAL ELEMENTS:
- Soft, flattering lighting with professional portrait techniques
- Intimate framing with professional depth of field
- Mirror shots with professional composition
- Nature elements with professional framing
- Visual bridges with professional color grading
- SHOT PATTERNS: Use "medium -> close-up -> medium" for emotional moments
- TIMING: Longer durations (6-7s) for medium shots of characters
- MUSIC SCORE: Emotional lo-fi piano with dreamy guitar samples and gentle wave atmospherics
"""
        elif genre == "action":
            genre_guidance = """
ACTION VISUAL ELEMENTS:
- Dynamic camera movements with professional tracking
- Strong directional lighting with professional contrast
- Low angles with professional composition
- Quick cutting with professional framing
- Environment interactions with professional effects
- SHOT PATTERNS: Use "wide -> wide -> wide" for action sequences
- TIMING: Shorter durations (2.0-2.5s) for fast-paced action
- MUSIC SCORE: Driving trap percussion with hard-hitting 808s and tense synth stabs
"""
        elif genre == "indie":
            genre_guidance = """
INDIE VISUAL ELEMENTS:
- Natural lighting with professional composition
- Handheld camera work with professional stabilization
- Authentic locations with professional framing
- Minimalist color grading with professional style
- Character-focused compositions with professional depth
- SHOT PATTERNS: Use "medium -> close-up -> medium" for intimate moments
- TIMING: Varied durations (3-5s) for natural pacing
- MUSIC SCORE: Lo-fi guitar textures with emo trap beats and nostalgic analog synths
"""
        elif genre == "post-apocalyptic":
            genre_guidance = """
POST-APOCALYPTIC VISUAL ELEMENTS:
- Desaturated color palette with professional grading
- Dust and debris effects with professional composition
- Abandoned environments with professional lighting
- Survival-focused framing with professional depth
- Atmospheric conditions with professional effects
- SHOT PATTERNS: Use "wide -> medium -> wide" for environment reveals
- TIMING: Longer durations (4-6s) for establishing shots
- MUSIC SCORE: Industrial ambient with distorted textures and sparse percussion
"""
        elif genre == "western":
            genre_guidance = """
WESTERN VISUAL ELEMENTS:
- Natural lighting with professional contrast
- Wide landscape shots with professional composition
- Dust and wind effects with professional framing
- Period-accurate locations with professional detail
- Dramatic silhouettes with professional lighting
- SHOT PATTERNS: Use "wide -> wide -> wide" for landscape reveals
- TIMING: Longer durations (5-7s) for establishing shots
- MUSIC SCORE: Latin-infused guitar interplay with desert atmospherics and minimal percussion
"""
        elif genre == "cyberpunk":
            genre_guidance = """
CYBERPUNK VISUAL ELEMENTS:
- Neon lighting with professional color grading
- Rain-slicked streets with professional reflections
- High-tech elements with professional lighting
- Urban decay with professional composition
- Futuristic architecture with professional framing
- SHOT PATTERNS: Use "wide -> medium -> wide" for technology reveals
- TIMING: Varied durations (2.5-4s) for dynamic scenes
- MUSIC SCORE: Industrial rhythms with chillwave textures and futuristic techno elements
"""
        elif genre == "fantasy":
            genre_guidance = """
FANTASY VISUAL ELEMENTS:
- Magical lighting with professional effects
- Mythical locations with professional composition
- Creature effects with professional integration
- Period-accurate elements with professional detail
- Enchanted atmosphere with professional grading
- SHOT PATTERNS: Use "wide -> medium -> wide" for magical reveals
- TIMING: Longer durations (4-6s) for establishing shots
- MUSIC SCORE: Ethereal bell textures with ancient instruments and ambient trap undercurrents
"""
        elif genre == "superhero":
            genre_guidance = """
SUPERHERO VISUAL ELEMENTS:
- Dynamic lighting with professional effects
- Heroic framing with professional composition
- Action sequences with professional choreography
- Power effects with professional integration
- Dramatic angles with professional camera work
- SHOT PATTERNS: Use "wide -> medium -> wide" for action sequences
- TIMING: Varied durations (2-4s) for dynamic scenes
- MUSIC SCORE: Bold brass themes with wave-influenced electronic production and melodic bass
"""
        elif genre == "blockbuster":
            genre_guidance = """
BLOCKBUSTER VISUAL ELEMENTS:
- Epic scale with professional composition
- High production value with professional effects
- Dynamic camera work with professional tracking
- Spectacular set pieces with professional choreography
- Dramatic lighting with professional contrast
- SHOT PATTERNS: Use "wide -> wide -> wide" for epic moments
- TIMING: Varied durations (3-6s) for dramatic impact
- MUSIC SCORE: Orchestral themes with modern electronic elements and powerful percussion
"""
        else:
            logger.warning(f"Unsupported genre: {genre}. Using default cinematic style.")
    
    chunk_prompt = f"""Create a compelling story about: {prompt}

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
    
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        temperature=0.7,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": chunk_prompt
            }
        ]
    )
    
    return parse_json_response(message.content[0].text)
CORS(app)
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
        num_sequences = data.get('num_sequences', 25)  # Default to 25 sequences
        
        # Calculate number of chunks needed based on requested sequence count
        # Each chunk will generate ~8-10 sequences
        sequences_per_chunk = 8
        total_chunks = max(3, math.ceil(num_sequences / sequences_per_chunk))
        
        # Ensure we have at least 3 chunks for proper 3-act structure
        if total_chunks < 3:
            total_chunks = 3
        
        # Generate first chunk (Act 1)
        first_chunk = generate_story_chunk(
            client, 
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
                client, 
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
        # Check if Anthropic API is available
        client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1,
            messages=[{"role": "user", "content": "test"}]
        )
        
        return jsonify({
            'status': 'healthy',
            'anthropic_status': 'connected'
        })
    except:
        return jsonify({
            'status': 'degraded',
            'anthropic_status': 'disconnected',
            'error': 'Cannot connect to Anthropic API'
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True) 