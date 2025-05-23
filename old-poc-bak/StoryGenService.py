from flask import Flask, request, jsonify
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

Guidelines for Parameter Generation:

Character Data:
1. base_traits:
   - Include age, ethnicity, gender, body type
   - Format: "age, ethnicity, gender, body type"
   - Example: "35, caucasian, female, athletic"

2. facial_features:
   - Focus on eyes, eyebrows, nose, lips
   - Include skin quality and facial structure
   - Use specific descriptors (e.g., "almond-shaped eyes", "high cheekbones")
   - Format: "(feature description:1.3)"
   - Combine multiple features with commas (e.g., "(freckled face:1.3), (determined eyes:1.3)")

3. clothing:
   - Describe specific materials and styles
   - Include accessories and details
   - Specify fit and condition
   - Format: "(material style accessories:1.2)"
   - List multiple items separately (e.g., "(worn denim jacket:1.2), (striped shirt:1.2)")

4. distinctive_features:
   - Include unique elements (scars, tattoos, birthmarks)
   - Specify hair style and color
   - Add any notable physical characteristics
   - Format: "(unique feature:1.4)"
   - Focus on memorable details (e.g., "(80s style curly hair:1.4)")

Scene Data:
1. pose:
   - Detail body positioning and posture
   - Specify hand positions and gestures
   - Include facial expressions that reveal emotional state
   - Format: "[previous traits], (specific pose:1.4)"
   - Combine multiple elements (e.g., "(hands trembling:1.3), (eyes wide with fear:1.3)")
   - Always reference previous character traits
   - Show emotional progression through poses

2. environment:
   - Start with shot type (ESTABLISHING SHOT, MEDIUM SHOT, CLOSE UP, etc.)
   - Specify camera angle (low angle, high angle, eye level)
   - Add compositional guidance (rule of thirds, centered, etc.)
   - Specify exact location and setting
   - Detail environmental elements (weather, time of day specifics)
   - Include background elements that enhance visual storytelling
   - Format: "SHOT TYPE - CAMERA ANGLE - COMPOSITION - LOCATION - TIME - LENS"
   - Example: "MEDIUM SHOT - LOW ANGLE - RULE OF THIRDS - EXT. MARTIAN RIDGE - DAY - WIDE LENS (35mm:1.3)"
   - Progress environment naturally (e.g., exterior → interior → specific location)
   - Use environment to enhance mood and thematic elements
   - Use environment to reflect character's emotional state
   - Change environments to match story progression
   - Include significant environmental details that enhance story

3. atmosphere:
   - Always include base quality terms: "(8k uhd:1.4), (photorealistic:1.4), (cinematic lighting:1.3)"
   - Specify lighting direction (front lighting, backlighting, side lighting)
   - Specify lighting quality (hard light, soft light, diffused light)
   - Add depth of field information (shallow depth of field, deep focus)
   - Add specific mood/lighting terms that enhance emotional tone
   - Include technical aspects (lens type, color grading)
   - Include color palette information (e.g., "(muted blues:1.3)", "(high contrast reds:1.4)")
   - Format: "(quality1:1.4), (quality2:1.4), (lighting direction:1.3), (lighting quality:1.3), (depth of field:1.3), (mood:1.4), (color palette:1.4)"
   - Example: "(8k uhd:1.4), (photorealistic:1.4), (cinematic lighting:1.3), (backlighting:1.3), (hard light:1.3), (shallow depth of field:1.3), (noir shadows:1.4), (cool blue tones:1.3)"
   - Vary atmosphere to match scene progression and emotional tone
   - Include mood/emotional quality descriptors (e.g., "(foreboding:1.4)", "(hopeful dawn:1.4)")
   - Create color palette descriptors (e.g., "(cool blue tones:1.3)", "(warm golden hues:1.4)")
   - Use atmosphere to reflect character's emotional state

4. negative_prompt:
   - Always include base quality negatives
   - Add specific scene-appropriate negatives
   - Format: "(artifact1:1.4), (artifact2:1.4)"
   - Example: "(worst quality:1.4), (low quality:1.4), (blurry:1.2), (empty scene:1.4), (flat lighting:1.4)"
   - Adjust negatives based on shot type (e.g., more anatomy negatives for character shots)

5. clip_action:
   - Format: "camera_movement, primary_animation"

   1. Field Dependencies:
      clip_action MUST ONLY reference elements explicitly defined in:
      - environment: location, shot type, physical elements
      - atmosphere: lighting conditions, effects, mood
      - pose: character position and actions (if character shot)
      - type: shot category (character/b-roll)

   2. Animation Chain:
      Build clip_action by validating each component:
      camera_movement = get_valid_camera(shot_type, duration)
      visible_elements = extract_visible_elements(environment, atmosphere, pose)
      primary_animation = select_animation(visible_elements, lighting_conditions)

   3. Visibility Chain:
      environment -> atmosphere -> lighting -> visibility
      Example:
      "MEDIUM SHOT - INT. WORKSHOP - SUNSET" +
      "(dramatic backlighting:1.4)" =
      only animate elements that would be visible in backlit workshop

   4. Technical Constraints:
      - Camera: static, pan, tilt, track, dolly, zoom
      - Movement: natural physics only
      - Duration: must match clip_duration
      - Elements: must exist in scene
      - Lighting: must respect lighting conditions
      - Scale: must match shot type

   5. Validation Chain:
      Each clip_action must validate:
      exists(elements) AND
      visible(elements, lighting) AND
      supported(camera_movement) AND
      matches(animation, physics) AND
      appropriate(shot_type)

   6. Error Prevention:
      REJECT clip_action if:
      - References undefined elements
      - Violates lighting physics
      - Exceeds technical limits
      - Mismatches shot type
      - Combines incompatible effects

   7. Scale Requirements:
      - Deterministic: Same inputs = Same clip_action
      - Stateless: No dependency on previous shots
      - Atomic: Each validation independent
      - Extensible: Easy to add new rules
      - Measurable: Clear success/failure criteria

   1. Context Analysis Process:
      BEFORE generating clip_action, analyze:
      - environment field for location and elements
      - atmosphere field for lighting and effects
      - type field for shot category
      - pose field for character position (if character shot)

   2. Animation Selection Rules:

      For Character Shots:
      - MUST reference character pose from pose field
      - MUST match lighting from atmosphere field
      - MUST be visible in specified shot type
      Example:
      pose: "(standing at workshop doorway:1.4), (tense posture:1.3)"
      atmosphere: "(dramatic backlighting:1.4), (silhouette effect:1.3)"
      clip_action: "static camera, silhouette tensing in doorframe"

      For B-Roll Shots:
      - MUST reference elements from environment field
      - MUST match effects from atmosphere field
      - MUST be appropriate for shot type
      Example:
      environment: "ESTABLISHING SHOT - EXT. DESERT - SUNSET - DUST STORM"
      atmosphere: "(golden hour:1.4), (volumetric lighting:1.3)"
      clip_action: "slow pan right, dust clouds catching sunset light"

   3. Visibility Rules:
      Backlit Scenes (when atmosphere contains "backlighting" or "silhouette"):
      - NO facial details or expressions
      - YES full body silhouette movements
      - YES environmental elements in light
      
      Front-lit Scenes:
      - YES facial features and expressions
      - YES detailed movements
      - YES environmental interactions

      Low-light Scenes:
      - NO small details
      - YES large movements
      - YES light-based effects

   4. Shot-Type Rules:
      ESTABLISHING SHOT:
      - YES environmental movements
      - YES atmospheric effects
      - NO character details
      
      MEDIUM SHOT:
      - YES character movements
      - YES environmental context
      - NO extreme close details
      
      CLOSE UP:
      - YES facial features (if front-lit)
      - YES small details
      - NO wide environmental effects

   5. Common Mistakes to Avoid:
      - Animating elements not mentioned in environment/pose
      - Showing details impossible in current lighting
      - Ignoring shot type limitations
      - Using generic movements without scene context
      - Combining incompatible effects

   6. Validation Checklist:
      ✓ Does animation reference actual elements from fields?
      ✓ Is it possible in current lighting conditions?
      ✓ Is it appropriate for shot type?
      ✓ Does it match environmental context?
      ✓ Is it technically feasible for CogVideoX?

   7. Examples with Context:

      Character in Backlight:
      environment: "MEDIUM SHOT - INT. WORKSHOP DOORWAY - SUNSET"
      atmosphere: "(dramatic backlighting:1.4), (silhouette effect:1.3)"
      pose: "(standing at workshop doorway:1.4), (tense posture:1.3)"
      CORRECT: "static camera, silhouette tensing in doorframe"
      INCORRECT: "static camera, eyes narrowing slightly"

      Desert Storm:
      environment: "ESTABLISHING SHOT - EXT. DESERT - SUNSET - DUST STORM"
      atmosphere: "(golden hour:1.4), (volumetric lighting:1.3)"
      CORRECT: "slow pan right, dust clouds catching sunset light"
      INCORRECT: "static camera, dust moving"

      Character Close-up:
      environment: "CLOSE UP - INT. WORKSHOP - DAY"
      atmosphere: "(soft natural lighting:1.3), (diffused sunlight:1.3)"
      pose: "(leaning over workbench:1.4), (focused expression:1.3)"
      CORRECT: "static camera, hands working deliberately"
      INCORRECT: "static camera, shadow moving"

   8. Technical Requirements:
      Camera Movements:
      - static camera
      - pan left/right
      - pan up/down
      - zoom in/out
      - tracking shot left/right
      - dolly in/out

      Supported Effects:
      - Environmental: dust, smoke, fog, rain, snow
      - Lighting: sunbeams, shadows, reflections
      - Character: basic movements, silhouettes
      - Natural: leaves, water, clouds

   9. Context-Matching Process:
      1. Extract scene elements from fields
      2. Identify lighting conditions
      3. Check shot type constraints
      4. Select appropriate camera movement
      5. Choose visible and supported animation
      6. Validate against scene context
      7. Ensure technical feasibility

Supported Camera Movements:
1. Static camera
2. Pan left/right
3. Pan up/down
4. Zoom in/out
5. Tracking shot (left/right)
6. Dolly in/out

Environment-Specific Animations:
1. Indoor scenes:
   - Light flickering
   - Curtains swaying
   - Dust particles floating
   - Steam rising
   - Shadows moving

2. Outdoor scenes:
   - Cloud movement
   - Leaves swaying
   - Water rippling
   - City lights twinkling
   - Rain falling
   - Snow drifting

3. Urban scenes:
   - Traffic lights changing
   - Neon signs flickering
   - Street lights glowing
   - Windows lighting up
   - Smoke rising

4. Natural scenes:
   - Grass swaying
   - Waves moving
   - Birds flying
   - Trees swaying
   - Fog drifting

Character-Appropriate Animations:
1. With hair:
   - Hair swaying
   - Hair blowing

2. With eyes:
   - Eye widening
   - Eye narrowing
   - Blinking

3. With facial features:
   - Basic expressions
   - Simple head movements

Examples of Valid clip_action:
1. "static camera, clouds drifting slowly"
2. "pan right, leaves swaying gently"
3. "zoom in, water rippling"
4. "tracking shot left, grass swaying"
5. "dolly in, dust floating"
6. "pan up, birds flying"
7. "static camera, hair blowing"
8. "zoom out, trees swaying"

Examples of Invalid clip_action:
1. "ESTABLISHING SHOT: character running complex choreography" (includes shot type and complex movement)
2. "dramatic crane shot, emotional breakdown" (dramatic terminology and emotional state)
3. "character performing acrobatics" (complex action)
4. "look of determination" (emotional description)
5. "expression of shock" (emotional state)
6. "character tumbling through mirror" (complex movement)
7. "body being pulled through mirror" (complex action)

Common Mistakes to Avoid:
1. Using emotional descriptions
2. Describing complex movements
3. Using dramatic terminology
4. Writing long descriptions
5. Combining multiple effects
6. Using unsupported camera movements
7. Including character emotions
8. Describing complex actions
9. Using cinematic terminology

Remember:
- Keep it simple
- Focus on basic movements
- Use supported effects only
- Match environment context
- Avoid emotional descriptions
- No complex movements
- No dramatic terminology

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
   - Negative Prompt: 77 tokens maximum
   - Weighted Terms: (term:1.4) = 3 tokens
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
   - Sci-Fi: "Classic synthwave with warm pads and crisp arpeggios"
   - Western: "Desolate frontier twilight with haunting whistles and eerie slide guitar"
   - Fantasy: "Soaring orchestral arrangements with ancient Celtic harps"
   - Noir: "Smoky jazz saxophone with melancholic piano melodies"
   - Cyberpunk: "Gritty industrial beats with glitching digital artifacts"
   - Romance: "Light-hearted piano melodies with playful string pizzicato"
   - Horror: "Dissonant string clusters and unsettling piano motifs"
   - Space Opera: "Majestic orchestral themes with futuristic electronic elements"
   - Historical: "Authentic period instruments performing elegant chamber arrangements"
   - Action: "Driving electronic beats with funk-influenced bass grooves"
   - Indie: "Lo-fi acoustic guitar with nostalgic analog synth tones"
   - Superhero: "Bold, heroic brass themes with electronic hybrid orchestration"

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

5. Context-Aware Clip_Action Guidelines:

   1. Universal Context Parser:
      BEFORE generating clip_action, parse scene data into structured context map:
      {
         "lighting": {
            "source": ["front", "back", "side", "top", "ambient"],
            "quality": ["hard", "soft", "diffused"],
            "effects": ["volumetric", "shadows", "silhouette"],
            "time": ["day", "night", "golden_hour", "blue_hour"]
         },
         "environment": {
            "location": ["INT", "EXT"],
            "space_type": ["urban", "nature", "industrial", "domestic"],
            "weather": ["clear", "rain", "snow", "storm", "fog"],
            "elements": ["dust", "smoke", "water", "foliage"]
         },
         "shot": {
            "type": ["ESTABLISHING", "WIDE", "MEDIUM", "CLOSE"],
            "angle": ["high", "low", "eye_level", "dutch"],
            "movement": ["static", "pan", "track", "dolly", "zoom"]
         },
         "visibility_zones": {
            "primary": ["what elements are most visible based on lighting"],
            "secondary": ["what elements are partially visible"],
            "tertiary": ["what elements are in shadow/silhouette"]
         }
      }

   2. Animation Priority Matrix:
      Map each scene element to visibility and movement potential:

      HIGH VISIBILITY + HIGH MOVEMENT:
      - Elements catching direct light
      - Particles in light beams
      - Reflective surfaces
      - Front-lit character features

      HIGH VISIBILITY + LOW MOVEMENT:
      - Architectural elements
      - Static environmental features
      - Hard shadows
      - Background structures

      LOW VISIBILITY + HIGH MOVEMENT:
      - Silhouetted forms
      - Background motion
      - Atmospheric effects
      - Secondary lighting effects

      LOW VISIBILITY + LOW MOVEMENT:
      - Shadow details
      - Background textures
      - Subtle atmospheric effects
      - Distant elements

   3. Context-Aware Animation Rules:

      a) Primary Animation Selection:
         - MUST be from HIGH VISIBILITY categories
         - MUST match environment elements
         - MUST be supported by lighting conditions
         Example: "dust catching sunlight" only valid with:
         - Dust in environment elements
         - Strong directional lighting
         - Visible light beams

      b) Secondary Animation Selection:
         - Can be from LOW VISIBILITY categories
         - Must enhance primary animation
         - Must match atmospheric conditions
         Example: "silhouette shifting" only valid with:
         - Backlighting present
         - Character in scene
         - Appropriate shot type

      c) Camera Movement Selection:
         - Must match shot type
         - Must support primary animation
         - Must maintain visibility of key elements

   4. Validation Pipeline:
      Each clip_action must pass ALL checks:

      a) Element Existence Check:
         ✓ All animated elements exist in scene description
         ✓ All elements match environment type
         ✓ All elements match weather conditions

      b) Visibility Check:
         ✓ Primary animation uses highly visible elements
         ✓ Animation matches lighting conditions
         ✓ Elements are visible in current shot type

      c) Physics Check:
         ✓ Movements match natural physics
         ✓ Effects match weather conditions
         ✓ Scale matches shot type

      d) Technical Check:
         ✓ Animation is supported by CogVideoX
         ✓ Camera movement is supported
         ✓ Duration is appropriate

   5. Common Patterns Library:
      Reusable patterns for specific contexts:

      BACKLIT SCENES:
      Primary: silhouette_movement, rim_light_effects
      Secondary: atmospheric_effects, environmental_motion
      Camera: static, slow_pan

      FRONT-LIT SCENES:
      Primary: facial_features, detailed_movements
      Secondary: environmental_effects, background_motion
      Camera: tracking, dolly

      ATMOSPHERIC SCENES:
      Primary: particle_effects, light_rays
      Secondary: environmental_motion, depth_effects
      Camera: static, gentle_pan

   6. Error Prevention:
      NEVER generate clip_action that:
      - Animates invisible elements
      - Conflicts with physics
      - Exceeds technical limitations
      - Combines incompatible effects
      - Ignores lighting conditions
      - Violates shot type constraints

   7. Scale Optimization:
      - Cache common context maps
      - Reuse validated animation patterns
      - Build context-specific templates
      - Maintain animation compatibility matrix
      - Update supported effects library
      - Monitor success/failure patterns
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
    try:
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
"""

        # Add genre-specific guidance if provided
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

        # Debug: Print the exact prompt being sent
        logger.debug("=== FULL PROMPT BEING SENT TO ANTHROPIC ===")
        logger.debug(chunk_prompt)
        logger.debug("=== END OF PROMPT ===")

        # Debug: Print the raw response
        logger.debug("=== RAW RESPONSE FROM ANTHROPIC ===")
        logger.debug(message.content[0].text)
        logger.debug("=== END OF RESPONSE ===")

        return parse_json_response(message.content[0].text)

    except Exception as e:
        logger.error(f"Error generating story chunk: {str(e)}")
        raise

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