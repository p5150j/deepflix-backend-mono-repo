import requests
import json
import time
import sys
import os
import logging
import argparse
from datetime import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import uuid
import shutil

# API endpoints
STORY_GEN_API = "http://10.0.0.14:5007/generate-cinematic-story"
IMAGE_GEN_API = "http://localhost:5000/generateImages"
VIDEO_GEN_API = "http://localhost:5001/generateVideos"
MUSIC_GEN_API = "http://localhost:5009/generate"

# Default values
DEFAULT_PROMPT = "Create a psychological thriller about Marcus, a shy 16-year-old boy who becomes increasingly obsessed with an underground social media platform that seems to predict world events with uncanny accuracy. As he delves deeper into the rabbit hole of conspiracy theories and personalized content, the boundary between reality and digital manipulation begins to blur. When his online mentor starts giving him 'missions' in the real world, Marcus must confront the possibility that he's being radicalized by an artificial intelligence designed to exploit psychological vulnerabilities. With his grasp on reality weakening and his relationships deteriorating, he must find a way to distinguish truth from manipulation before he loses himself completely to the digital labyrinth."
DEFAULT_GENRE = "psychological thriller"
DEFAULT_NUM_SEQUENCES = 50

def setup_logging():
    """Set up logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create a unique log file for this run
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = f'logs/api_interactions_{timestamp}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger()

def setup_session():
    """Set up a request session with retry logic and extended timeouts"""
    session = requests.Session()
    
    # Configure retry strategy
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST", "GET"]
    )
    
    # Configure adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    
    return session

def generate_story(prompt, genre="indie", num_sequences=50):
    """Generate a story using the new API structure."""
    try:
        payload = {
            "prompt": prompt,
            "genre": genre,
            "num_sequences": num_sequences
        }
        
        print("\n📝 Generating story...")
        print(f"Prompt: {prompt}")
        print(f"Genre: {genre}")
        print(f"Number of sequences: {num_sequences}")
        
        response = requests.post(STORY_GEN_API, json=payload)
        
        if response.status_code == 200:
            story_data = response.json()
            print("✅ Story generated successfully!")
            
            # Log music score data if present
            if "music_score" in story_data:
                music_score = story_data["music_score"]
                print("\n🎵 Music Score Details:")
                print(f"Instrumentation: {music_score.get('instrumentation', 'N/A')}")
                print(f"Style: {music_score.get('style', 'N/A')}")
                print(f"Tempo: {music_score.get('tempo', 'N/A')}")
                print(f"Type: {music_score.get('type', 'N/A')}")
            
            return story_data
        else:
            print(f"❌ Failed to generate story: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating story: {str(e)}")
        return None

def generate_images(sequence_data, character_data, music_score, folder_id):
    """Generate images for the story sequences."""
    try:
        payload = {
            "character": character_data,
            "sequence": sequence_data,
            "music_score": music_score,  # Add music score to payload
            "seed": 952521,
            "sampler": "euler",
            "steps": 20,
            "cfg_scale": 7
        }
        
        print("\n🎨 Generating images...")
        print(f"Music Score Type: {music_score.get('type', 'N/A')}")  # Log music score type
        response = requests.post(IMAGE_GEN_API, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Images generated successfully!")
            return result
        else:
            print(f"❌ Failed to generate images: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating images: {str(e)}")
        return None

def generate_videos(folder_id, sequence_data, music_score):
    """Generate videos for the story sequences."""
    try:
        payload = {
            "sequence": sequence_data,
            "music_score": music_score  # Add music score to payload
        }
        
        print("\n🎬 Generating videos...")
        print(f"Music Score Style: {music_score.get('style', 'N/A')}")  # Log music score style
        response = requests.post(f"{VIDEO_GEN_API}/{folder_id}", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Videos generated successfully!")
            return result
        else:
            print(f"❌ Failed to generate videos: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating videos: {str(e)}")
        return None

def generate_music(music_score, output_dir, audio_length=95):
    """Generate music based on the music score data."""
    try:
        # Convert music score data to comma-separated string
        ref_prompt = ", ".join([
            f"instrumentation: {music_score.get('instrumentation', '')}",
            f"style: {music_score.get('style', '')}",
            f"tempo: {music_score.get('tempo', '')}",
            f"type: {music_score.get('type', '')}"
        ])
        
        # Use the same output directory as images
        output_path = os.path.join("/home/dev/Desktop/ComfyUI/output/output", output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        payload = {
            "ref_prompt": ref_prompt,
            "audio_length": audio_length,
            "repo_id": "ASLP-lab/DiffRhythm-base",
            "output_dir": output_path,
            "chunked": True
        }
        
        print("\n🎵 Generating music...")
        print("Sending payload:")
        print(json.dumps(payload, indent=2))
        
        response = requests.post(MUSIC_GEN_API, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Music generated successfully!")
            print("Response object:")
            print(json.dumps(result, indent=2))
            
            # Check if the file was created in the correct location
            output_file = os.path.join(output_path, "output.wav")
            if os.path.exists(output_file):
                print(f"\n✅ Music file generated at: {output_file}")
                return result
            else:
                print(f"❌ Generated music file not found at: {output_file}")
                return None
        else:
            print(f"❌ Failed to generate music: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating music: {str(e)}")
        return None

def load_sequence_data(output_folder):
    """Load sequence data from the output folder"""
    try:
        # Look for sequence.json in the output folder
        sequence_file = os.path.join(output_folder, "sequence.json")
        if not os.path.exists(sequence_file):
            print(f"❌ No sequence.json found in {output_folder}")
            return None
            
        with open(sequence_file, 'r') as f:
            sequence_data = json.load(f)
            
        print(f"✅ Loaded sequence data with {len(sequence_data)} items")
        return sequence_data
        
    except Exception as e:
        print(f"❌ Error loading sequence data: {str(e)}")
        return None

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate a cinematic story with images and videos')
    
    parser.add_argument('--prompt', type=str, default=DEFAULT_PROMPT,
                        help='The prompt for story generation')
    
    parser.add_argument('--genre', type=str, default=DEFAULT_GENRE,
                        help='The genre of the story')
    
    parser.add_argument('--num-sequences', type=int, default=DEFAULT_NUM_SEQUENCES,
                        help='The number of sequences to generate')
    
    return parser.parse_args()

def main():
    """Main function to run the pipeline."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Use the provided arguments or defaults
    prompt = args.prompt
    genre = args.genre
    num_sequences = args.num_sequences
    
    print("\n=== Story Generation Pipeline ===")
    print(f"Prompt: {prompt}")
    print(f"Genre: {genre}")
    print(f"Number of sequences: {num_sequences}")
    
    # Generate story
    story_data = generate_story(prompt, genre=genre, num_sequences=num_sequences)
    if not story_data:
        print("❌ Failed to generate story. Exiting.")
        return
        
    # Extract sequence, character, and music score data
    sequence_data = story_data.get("sequence", [])
    character_data = story_data.get("character", {})
    music_score = story_data.get("music_score", {})
    
    if not sequence_data or not character_data:
        print("❌ Invalid story data. Exiting.")
        return
        
    # Generate images
    image_result = generate_images(sequence_data, character_data, music_score, None)
    if not image_result:
        print("❌ Failed to generate images. Exiting.")
        return
        
    folder_id = image_result.get("folder_id")
    if not folder_id:
        print("❌ No folder ID returned. Exiting.")
        return
        
    # Generate music
    music_result = generate_music(music_score, folder_id)
    if not music_result:
        print("❌ Failed to generate music. Exiting.")
        return
        
    # Generate videos
    video_result = generate_videos(folder_id, sequence_data, music_score)
    if not video_result:
        print("❌ Failed to generate videos. Exiting.")
        return
        
    print("\n✅ Pipeline completed successfully!")
    print(f"Output folder: {folder_id}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total execution time: {(end_time - start_time) / 60:.2f} minutes")