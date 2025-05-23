import json
import os
import time
import subprocess
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib import request as url_request
import glob
import random
from dotenv import load_dotenv

from services.narration_service import generate_narration, estimate_text_duration, adjust_text_for_duration, select_voice
from services.music_service import generate_music_score, add_background_music
from services.firebase_service import validate_firebase_connections, upload_video_to_firebase, update_firestore_with_video_url
from services.media_service import merge_video_audio, concatenate_videos

# Load environment variables
load_dotenv()

# API Config
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_BASE_DIR = os.path.expanduser("~/Desktop/ComfyUI")
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_BASE_DIR, "output", "output")
TTS_API_URL = "http://localhost:5010/generate-voice"
MUSIC_GEN_API_URL = "http://localhost:5009/generate"
VIDEO_GENERATION_TIMEOUT = 1800  # 30 minutes timeout

app = Flask(__name__)
CORS(app)

# Validate Firebase connections on startup
validate_firebase_connections()

def format_sequence_number(num):
    """Formats a number into a 4-digit string (e.g., 1 -> '0001')."""
    return f"{num:04d}"

def check_video(output_folder, expected_video):
    """Check if a video exists and is valid."""
    # Check for all possible video patterns we've seen
    video_patterns = [
        os.path.join(output_folder, f"{expected_video}.mp4"),
        os.path.join(output_folder, f"{expected_video}_00001.mp4"),
        os.path.join(output_folder, f"{expected_video}__00001.mp4")
    ]
        
    for video_path in video_patterns:
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            print(f"✅ Found valid video: {os.path.basename(video_path)}")
            return True
                
    return False

def validate_clip_action(clip_action, duration):
    """Validate and simplify clip_action based on duration"""
    # Extract movements from clip_action
    movements = [m.strip() for m in clip_action.split(',')]
    
    # Define movement limits based on duration
    max_movements = {
        3: 1,  # 3 seconds = 1 movement
        5: 2,  # 5 seconds = 2 movements
        7: 3   # 7 seconds = 3 movements
    }.get(duration, 2)
    
    # Take only the first N movements
    validated_movements = movements[:max_movements]
    
    return ', '.join(validated_movements)

def build_video_workflow(image_path, clip_action, output_folder, clip_duration=3.0625, transition_type="none", seed=1):
    """Constructs the ComfyUI workflow for video generation."""
    # Cap clip_duration at 6 seconds to prevent OOM
    clip_duration = min(float(clip_duration), 6.0)
    
    # Calculate frames based on duration + 1 second buffer
    FPS = 24
    buffered_duration = clip_duration + 0.5  # Add 0.5 second buffer
    num_frames = int(buffered_duration * FPS)
    
    # Get the base filename without extension
    base_filename = os.path.splitext(os.path.basename(image_path))[0]
    
    # Validate and simplify clip_action
    validated_clip_action = validate_clip_action(clip_action, clip_duration)
    
    # Log the clip_action changes
    print("\n🎬 Clip Action Validation:")
    print(f"Original clip_action: {clip_action}")
    print(f"Validated clip_action: {validated_clip_action}")
    
    addFix = "consistent lighting throughout, well-lit scene, maintained brightness, "
    # Define prompts
    positive_prompt = addFix + validated_clip_action
    
    # Optimized negative prompts with higher weights for critical issues
    negative_prompt = (
        "darkening, underexposed, fading to black, vignetting"
        # Critical face/hand issues (highest priority)
        "(distorted face:1.8), (melting face:1.8), (morphed face:1.8), "
        "(distorted hands:1.8), (extra fingers:1.8), (missing fingers:1.8), "
        
        # Movement and temporal issues
        "(temporal inconsistency:1.8), (frame artifacts:1.8), "
        "(unnatural movement:1.6), (jittering:1.6), (warping:1.6), "
       
        
        # B-roll specific issues
        "(blurry background:1.7), (wavy background:1.7), "
        "(color bleeding:1.6), (lighting inconsistency:1.6), "
        
        # General quality issues
        "(worst quality:1.4), (low quality:1.4), (blurry:1.4), "
        "(artifacts:1.4), (pixelated:1.4), "
        
        # Style and composition
        "(bad composition:1.3), (poor framing:1.3), "
        "(unnatural colors:1.3), (oversaturated:1.3), "
        
        # Safety
        "(text:1.2), (watermark:1.2), (logo:1.2)"
    )

    # Log the prompts and timing
    print("\n🎬 Video Generation Prompts:")
    print(f"Positive Prompt: {positive_prompt}")
    print(f"Negative Prompt: {negative_prompt}")
    print(f"Original Duration: {clip_duration}s")
    print(f"Buffered Duration: {buffered_duration}s")
    print(f"Total Frames: {num_frames}")
    print(f"Using seed: {seed}")
    
    workflow = {
        "20": {
            "inputs": {
                "clip_name": "t5/google_t5-v1_1-xxl_encoderonly-fp8_e4m3fn.safetensors",
                "type": "sd3",
                "device": "default"
            },
            "class_type": "CLIPLoader"
        },
        "30": {
            "inputs": {
                "prompt": positive_prompt,
                "strength": 1,
                "force_offload": False,
                "clip": ["20", 0]
            },
            "class_type": "CogVideoTextEncode"
        },
        "31": {
            "inputs": {
                "prompt": negative_prompt,
                "strength": 1,
                "force_offload": True,
                "clip": ["30", 1]
            },
            "class_type": "CogVideoTextEncode"
        },
        "36": {
            "inputs": {
                "image": image_path
            },
            "class_type": "LoadImage"
        },
        "37": {
            "inputs": {
                "width": 1024,
                "height": 576,
                "upscale_method": "lanczos",
                "keep_proportion": True,
                "divisible_by": 16,
                "crop": "disabled",
                "image": ["36", 0]
            },
            "class_type": "ImageResizeKJ"
        },
        "44": {
            "inputs": {
                "frame_rate": FPS,
                "loop_count": 0,
                "filename_prefix": os.path.join(output_folder, base_filename),
                "format": "video/h264-mp4",
                "pix_fmt": "yuv420p",
                "crf": 5,              # Changed from 19 to 5 for better quality
                "save_metadata": True,
                "trim_to_audio": False,
                "pingpong": False,
                "save_output": True,
                "save_frames": False,
                "images": ["65", 0]    # Changed from 60 to 65 to use RIFE output
            },
            "class_type": "VHS_VideoCombine"
        },
        "59": {
            "inputs": {
                "model": "kijai/CogVideoX-5b-1.5-I2V",
                "precision": "bf16",
                "quantization": "disabled",
                "enable_sequential_cpu_offload": False,
                "attention_mode": "sdpa",
                "load_device": "main_device"
            },
            "class_type": "DownloadAndLoadCogVideoModel"
        },
        "60": {
            "inputs": {
                "enable_vae_tiling": True,
                "tile_sample_min_height": 240,
                "tile_sample_min_width": 360,
                "tile_overlap_factor_height": 0.2,
                "tile_overlap_factor_width": 0.2,
                "auto_tile_size": True,
                "vae": ["59", 1],
                "samples": ["63", 0]
            },
            "class_type": "CogVideoDecode"
        },
        "62": {
            "inputs": {
                "enable_tiling": False,
                "noise_aug_strength": 0,
                "strength": 1,
                "start_percent": 0,
                "end_percent": 1,
                "vae": ["59", 1],
                "start_image": ["37", 0]
            },
            "class_type": "CogVideoImageEncode"
        },
        "63": {
            "inputs": {
                "num_frames": num_frames,  # Use exact calculated frames
                "steps": 30,
                "cfg": 7.0,
                "seed": seed,  # Use the provided seed
                "scheduler": "CogVideoXDDIM",
                "denoise_strength": 0.60,
                "model": ["59", 0],
                "positive": ["30", 0],
                "negative": ["31", 0],
                "image_cond_latents": ["62", 0]
            },
            "class_type": "CogVideoSampler"
        },
        "65": {                        # Added RIFE VFI node for frame interpolation
            "inputs": {
                "ckpt_name": "rife47.pth",
                "clear_cache_after_n_frames": 20,
                "multiplier": 2.0,      # Changed from 2.0 to 1.0 for more natural motion
                "fast_mode": False,
                "ensemble": True,
                "scale_factor": 1,
                "frames": ["60", 0]
            },
            "class_type": "RIFE VFI"
        }
    }
    
    return workflow

def setup_detailed_logging(folder_id):
    """Set up detailed logging for the video generation process"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(COMFYUI_OUTPUT_DIR, folder_id, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, "video_generation.log")),
            logging.StreamHandler()
        ]
    )
    
    # Disable debug logging for requests and urllib3
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    # Comment out the following line to disable ComfyUI API polling debug logs
    # logging.getLogger("http.client").setLevel(logging.DEBUG)
    
    return logging.getLogger(__name__)

def log_processing_stats(logger, sequence_data, processed_scenes):
    """Log detailed processing statistics"""
    logger.info("\n=== Processing Statistics ===")
    logger.info(f"Total scenes in sequence: {len(sequence_data)}")
    logger.info(f"Successfully processed scenes: {len(processed_scenes)}")
    
    # Log scene-by-scene breakdown
    for item in sequence_data:
        scene_key = f"{item['sequence_number']}_{item['type']}"
        status = "Processed" if scene_key in processed_scenes else "Skipped"
        logger.info(f"Scene {item['sequence_number']} ({item['type']}): {status}")
    
    logger.info("=== End Statistics ===\n")

def process_video_generation(folder_id, data):
    """Process video generation for a sequence of images in strict sequential order."""
    output_folder = os.path.join(COMFYUI_OUTPUT_DIR, folder_id)
    
    if not data or "sequence" not in data:
        print("❌ No sequence data provided")
        return {"status": "error", "message": "No sequence data provided"}
    
    sequence_data = data["sequence"]
    print(f"\nStarting video generation for {len(sequence_data)} scenes...")
    print(f"Output folder: {output_folder}")
    
    # Get the seed from the request data
    seed = data.get("seed", 1)
    print(f"\nUsing seed from request: {seed}")
    
    # Debug sequence data
    print("\nSequence Data Structure:")
    print(json.dumps(sequence_data, indent=2))
    
    # Phase 1: Generate background music
    print("\n=== Phase 1: Generating Background Music ===")
    music_score = data.get("music_score")
    
    if music_score:
        print("Found music score in data")
        success = generate_music_score(output_folder, music_score)
        if not success:
            return {"status": "error", "message": "Failed to generate background music"}
    else:
        print("No music score found in data")
    
    # Phase 2: Generate all videos
    print("\n=== Phase 2: Generating Videos ===")
    for item in sequence_data:
        scene_number = item.get("sequence_number")
        if not scene_number:
            continue
            
        print(f"\nProcessing scene {scene_number}...")
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        video_file = os.path.join(output_folder, f"{base_name}__00001.mp4")
        
        success = generate_video(
            os.path.join(output_folder, f"{base_name}.png"),
            video_file,
            item.get("clip_duration", 3.0625),
            item.get("clip_action"),
            seed  # Pass the seed to generate_video
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate video for scene {scene_number}"}
    
    # Select voice once for the entire movie
    selected_voice = select_voice(data.get("character"))
    print(f"\n🎙️ Selected voice for entire movie: {selected_voice}")
    
    # Phase 3: Generate all audio
    print("\n=== Phase 3: Generating Audio ===")
    for item in sequence_data:
        if "voice_narration" not in item:
            continue
            
        scene_number = item.get("sequence_number")
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        
        print(f"\nGenerating audio for scene {scene_number}...")
        success = generate_narration(
            item["voice_narration"],
            os.path.join(output_folder, f"{base_name}.png"),
            output_folder,
            setup_detailed_logging(folder_id),
            data.get("character"),  # Pass the character data
            selected_voice  # Pass the pre-selected voice
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate audio for scene {scene_number}"}
    
    # Phase 4: Merge videos with audio
    print("\n=== Phase 4: Merging Videos with Audio ===")
    video_files = sorted(glob.glob(os.path.join(output_folder, "scene_*_*_00001__00001.mp4")))
    merged_videos = []
    
    for video_file in video_files:
        base_name = os.path.splitext(os.path.basename(video_file))[0].replace("__00001", "")
        merged_output = os.path.join(output_folder, f"{base_name}_final.mp4")
        
        print(f"\nProcessing video: {base_name}")
        
        audio_patterns = [
            os.path.join(output_folder, f"{base_name}__00001.wav"),
            os.path.join(output_folder, f"{base_name}__00001_.wav"),
            os.path.join(output_folder, f"{base_name}___00001_.wav")
        ]
        
        audio_file = None
        for pattern in audio_patterns:
            if os.path.exists(pattern):
                audio_file = pattern
                print(f"Found audio file: {pattern}")
                break
        
        if audio_file:
            print(f"Merging with audio file: {audio_file}")
            success = merge_video_audio(video_file, audio_file, merged_output)
            if success:
                merged_videos.append(merged_output)
        else:
            print(f"No audio file found for: {base_name} - skipping")
            continue
    
    # Phase 5: Concatenate all scenes
    print("\n=== Phase 5: Concatenating All Scenes ===")
    success = concatenate_videos(output_folder)
    
    if not success:
        return {"status": "error", "message": "Failed to concatenate videos"}
    
    # Phase 6: Add background music
    print("\n=== Phase 6: Adding Background Music ===")
    if music_score:
        success = add_background_music(output_folder)
        if not success:
            return {"status": "error", "message": "Failed to add background music"}
        print("✅ Background music added successfully")
    
    print("\n✅ All video generation phases completed successfully")
    return {"status": "success", "message": "Video generation completed"}

def generate_video(image_path, output_path, clip_duration=5, clip_action=None, seed=1):
    """Generate a video from an image using ComfyUI."""
    try:
        # Calculate frames based on duration + 1 second buffer
        FPS = 24
        buffered_duration = clip_duration + 0.5  # Add 1 second buffer
        num_frames = int(buffered_duration * FPS)
        
        # Get the base filename without extension
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        
        # Use the provided clip_action for the positive prompt
        positive_prompt = clip_action if clip_action else "cinematic shot, high quality, detailed, sharp focus"
        
        # Log the prompts and timing
        print("\n🎬 Video Generation Settings:")
        print(f"Input image: {image_path}")
        print(f"Output path: {output_path}")
        print(f"Positive Prompt: {positive_prompt}")
        print(f"Original Duration: {clip_duration}s")
        print(f"Buffered Duration: {buffered_duration}s")
        print(f"Total Frames: {num_frames}")
        print(f"Using seed: {seed}")
        print(f"Timeout: {VIDEO_GENERATION_TIMEOUT} seconds")
        
        # Build the workflow
        workflow = build_video_workflow(
            image_path,
            positive_prompt,
            os.path.dirname(output_path),
            clip_duration=clip_duration,
            seed=seed
        )
        
        # Check if video already exists and is valid
        if check_video(os.path.dirname(output_path), base_filename):
            print(f"✅ Video already exists and is valid: {base_filename}")
            return True
            
        # Send request to ComfyUI API
        print("\nSending request to ComfyUI API...")
        response = requests.post(COMFYUI_API_URL, json={"prompt": workflow})
        
        if response.status_code != 200:
            print(f"❌ API request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        try:
            response_data = response.json()
            prompt_id = response_data.get("prompt_id")
            if not prompt_id:
                print("❌ No prompt_id in response")
                return False
                
            # Wait for the video generation to complete
            print("\n⏳ Waiting for video generation to complete...")
            start_time = time.time()
            last_progress = 0
            last_status = None
            completion_detected = False
            
            while time.time() - start_time < VIDEO_GENERATION_TIMEOUT:
                # Check queue status
                queue_response = requests.get("http://127.0.0.1:8188/queue")
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    if "queue_running" in queue_data and prompt_id in queue_data["queue_running"]:
                        elapsed_time = int(time.time() - start_time)
                        current_status = f"🎬 Video generation in progress... ({elapsed_time}/{VIDEO_GENERATION_TIMEOUT}s)"
                        if current_status != last_status:
                            print(current_status)
                            last_status = current_status
                        time.sleep(2)
                        continue
                
                # Check history status
                history_response = requests.get("http://127.0.0.1:8188/history")
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    if prompt_id in history_data:
                        print("✅ Video generation completed!")
                        time.sleep(2)
                        if check_video(os.path.dirname(output_path), base_filename):
                            completion_detected = True
                            break
                
                # Check file growth
                video_patterns = [
                    os.path.join(os.path.dirname(output_path), f"{base_filename}.mp4"),
                    os.path.join(os.path.dirname(output_path), f"{base_filename}_00001.mp4"),
                    os.path.join(os.path.dirname(output_path), f"{base_filename}__00001.mp4")
                ]
                
                for video_path in video_patterns:
                    if os.path.exists(video_path):
                        current_size = os.path.getsize(video_path)
                        if current_size > last_progress:
                            elapsed_time = int(time.time() - start_time)
                            print(f"📊 Video file growing: {current_size/1024:.1f} KB ({elapsed_time}/{VIDEO_GENERATION_TIMEOUT}s)")
                            last_progress = current_size
                            last_status = f"📊 Video file growing: {current_size/1024:.1f} KB"
                
                time.sleep(2)
            
            if not completion_detected:
                print(f"❌ Video generation timed out after {VIDEO_GENERATION_TIMEOUT} seconds")
                return False
                
            # Add a small delay after completion to ensure file system sync
            time.sleep(2)
            return True
                
        except json.JSONDecodeError:
            print("❌ Failed to parse API response as JSON")
            print(f"Raw response: {response.text[:500]}...")
            return False

    except Exception as e:
        print(f"❌ Error generating video: {str(e)}")
        return False

@app.route("/generateVideos/<folder_id>", methods=["POST"])
def generate_videos(folder_id):
    """API endpoint to generate images for a sequence of shots."""
    try:
        data = request.get_json()
        if not data or "sequence" not in data:
            return jsonify({"status": "error", "message": "No sequence data provided"}), 400
            
        # Set up detailed logging
        logger = setup_detailed_logging(folder_id)
        logger.info(f"Starting video generation for folder: {folder_id}")
        
        # Process videos with detailed logging, passing the entire data object
        result = process_video_generation(folder_id, data)
        
        # Log final statistics
        logger.info("Video generation process completed")
        logger.info(f"Final result: {result}")
        
        # Get the final video path from the output folder
        output_folder = os.path.join(COMFYUI_OUTPUT_DIR, folder_id)
        final_video_path = os.path.join(output_folder, "final_movie_with_music_smooth.mp4")
        
        if not os.path.exists(final_video_path):
            return jsonify({"error": "Final video not found"}), 500

        # Upload video to Firebase using folder_id as movie_id
        try:
            video_url = upload_video_to_firebase(final_video_path, folder_id)
            update_firestore_with_video_url(folder_id, video_url)
        except Exception as e:
            logger.error(f"Error uploading to Firebase: {str(e)}")
            return jsonify({"error": "Failed to upload video to Firebase"}), 500

        return jsonify({
            "message": "Video generated and uploaded successfully",
            "video_url": video_url
        }), 200

    except Exception as e:
        logger.error(f"Error in video generation: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 