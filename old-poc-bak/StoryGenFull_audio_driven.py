import json
import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from urllib import request as url_request
import glob
import shutil
import time
import requests
import logging
import subprocess

# API Config
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_BASE_DIR = os.path.expanduser("~/Desktop/ComfyUI")
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_BASE_DIR, "output", "output")
OUTPUT_BASE_DIR = "output"

# Add TTS API URL
TTS_API_URL = "http://localhost:5005/tts"

# Audio-driven video generation constants
AUDIO_PADDING = 0.5  # seconds of padding for cinematic flow
DURATION_TOLERANCE = 0.1  # seconds tolerance for duration matching
FPS = 16  # frames per second for video generation

app = Flask(__name__)

def get_media_duration(file_path):
    """Get the duration of a media file using ffprobe."""
    try:
        cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except Exception as e:
        print(f"Error getting duration for {file_path}: {str(e)}")
        return None

def validate_media_file(file_path, file_type="audio"):
    """Validate a media file's existence and validity."""
    if not os.path.exists(file_path):
        print(f"❌ {file_type.capitalize()} file not found: {file_path}")
        return False
    
    try:
        duration = get_media_duration(file_path)
        if duration is None or duration <= 0:
            print(f"❌ Invalid {file_type} duration for {file_path}")
            return False
        return True
    except Exception as e:
        print(f"❌ Error validating {file_type} file {file_path}: {str(e)}")
        return False

def analyze_audio_durations(output_folder, sequence_data):
    """Analyze audio durations and create a mapping for video generation."""
    duration_map = {}
    total_duration = 0
    max_duration = 0
    min_duration = float('inf')
    
    print("\n=== Audio Duration Analysis ===")
    
    for item in sequence_data:
        scene_number = item.get("sequence_number")
        scene_type = item.get("type", "character")
        base_name = f"scene_{format_sequence_number(scene_number)}_{scene_type}_00001_"
        audio_file = os.path.join(output_folder, f"{base_name}*.wav")  # Use wildcard for audio file
        
        # Find the actual audio file using glob
        audio_files = glob.glob(audio_file)
        if not audio_files:
            print(f"❌ No audio file found for scene {scene_number}")
            continue
            
        # Use the first matching audio file
        actual_audio_file = audio_files[0]
        
        if not validate_media_file(actual_audio_file, "audio"):
            print(f"❌ Skipping invalid audio file for scene {scene_number}")
            continue
            
        duration = get_media_duration(actual_audio_file)
        if duration is not None:
            duration_with_padding = duration + AUDIO_PADDING
            duration_map[scene_number] = {
                "original_duration": duration,
                "padded_duration": duration_with_padding,
                "base_clip_duration": item.get("clip_duration", 3.0625)
            }
            
            total_duration += duration
            max_duration = max(max_duration, duration)
            min_duration = min(min_duration, duration)
            
            print(f"Scene {scene_number}:")
            print(f"  Original duration: {duration:.2f}s")
            print(f"  With padding: {duration_with_padding:.2f}s")
            print(f"  Base clip duration: {item.get('clip_duration', 3.0625):.2f}s")
    
    if duration_map:
        avg_duration = total_duration / len(duration_map)
        print("\nDuration Statistics:")
        print(f"Total scenes analyzed: {len(duration_map)}")
        print(f"Average duration: {avg_duration:.2f}s")
        print(f"Maximum duration: {max_duration:.2f}s")
        print(f"Minimum duration: {min_duration:.2f}s")
    
    return duration_map

def should_adjust_clip_duration(audio_info):
    """Determine if clip duration needs adjustment based on audio duration."""
    MAX_DURATION = 8.0  # Maximum duration in seconds (128 frames at 16 FPS)
    MIN_DURATION = 1.5  # Minimum duration in seconds
    
    # First, ensure we're within the absolute limits
    if audio_info["padded_duration"] > MAX_DURATION:
        print(f"[WARNING] Audio duration {audio_info['padded_duration']:.2f}s exceeds maximum allowed duration of {MAX_DURATION}s")
        print(f"  Capping video duration at {MAX_DURATION}s")
        return True, MAX_DURATION
        
    if audio_info["padded_duration"] < MIN_DURATION:
        print(f"[WARNING] Audio duration {audio_info['padded_duration']:.2f}s is below minimum duration of {MIN_DURATION}s")
        print(f"  Setting video duration to {MIN_DURATION}s")
        return True, MIN_DURATION
    
    # Then check if we need to adjust based on audio duration
    if audio_info["padded_duration"] > audio_info["base_clip_duration"]:
        return True, audio_info["padded_duration"]
        
    return False, audio_info["base_clip_duration"]

def generate_unique_output_folder():
    """Generate a unique folder name with timestamp and UUID."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    folder_name = f"{timestamp}-{unique_id}"
    return os.path.join(COMFYUI_OUTPUT_DIR, folder_name)

def format_sequence_number(num):
    """Formats a number into a 4-digit string (e.g., 1 -> '0001')."""
    return f"{num:04d}"

def wait_for_images(output_folder, expected_count, timeout=900):
    """Wait for all images to be generated."""
    start_time = time.time()
    check_interval = 5  # Check every 5 seconds
    last_count = 0
    
    while time.time() - start_time < timeout:
        # Get all generated images
        image_files = glob.glob(os.path.join(output_folder, "scene_*_*.png"))
        current_count = len(image_files)
        
        # Print progress if count changed
        if current_count != last_count:
            print(f"Generated {current_count}/{expected_count} images...")
            last_count = current_count
        
        if current_count >= expected_count:
            print(f"✅ All {expected_count} images generated successfully!")
            return True
            
        time.sleep(check_interval)
    
    print(f"❌ Timeout waiting for image generation. Generated {last_count}/{expected_count} images.")
    return False

def build_character_prompt(character_data):
    """Builds a structured character prompt with weighted emphasis on key features."""
    base_traits = character_data.get("base_traits", "")
    facial_features = character_data.get("facial_features", "")
    clothing = character_data.get("clothing", "")
    distinctive_features = character_data.get("distinctive_features", "")
    
    # Build prompt with weighted emphasis on key identifying features
    prompt = f"{base_traits}, {facial_features}, {clothing}, {distinctive_features}"
    return prompt

def build_image_workflow(sequence_data, character_data, seed, sampler, steps, cfg_scale, output_folder, global_negative_prompt=None):
    """Constructs the ComfyUI workflow for image generation."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "SD1.5/epicphotogasm_ultimateFidelity.safetensors"}
        },
        "2": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": 576,    # HD aspect ratio (16:9) height
                "width": 1024    # HD aspect ratio (16:9) width
            }
        }
    }

    # Build the character prompt once to ensure consistency
    character_prompt = build_character_prompt(character_data)
    base_seed = seed

    node_id = 3
    output_nodes = []

    for scene in sequence_data:
        scene_type = scene.get("type", "character")
        sequence_number = scene.get("sequence_number", 0)
        
        if scene_type == "character":
            # Character scene: Use consistent character prompt with scene-specific elements
            full_prompt = f"{character_prompt}, {scene['pose']}, {scene['environment']}, {scene.get('atmosphere', '')}"
            # Use base seed for character elements to maintain consistency
            scene_seed = base_seed
        else:
            # B-roll scene: Focus on environment
            full_prompt = f"{scene['environment']}, {scene.get('atmosphere', '')}, cinematic composition, dramatic lighting"
            # Use sequence-modified seed for variety in non-character scenes
            scene_seed = base_seed + sequence_number

        # Log the prompts for this scene
        print(f"\n🎨 Image Generation Prompts for Scene {sequence_number}:")
        print(f"Scene Type: {scene_type}")
        print(f"Positive Prompt: {full_prompt}")
        
        # Negative prompt encoding
        scene_negative = scene.get("negative_prompt", "")
        base_negative = global_negative_prompt if global_negative_prompt else "(worst quality, low quality:1.4), (blurry:1.2), watermark, signature, text, logo"
        
        if scene_type == "character":
            negative_text = f"{base_negative}, {scene_negative}, (multiple people:1.8), (two women:1.8), (two persons:1.8), (twins:1.8), (multiple subjects:1.8), (group of people:1.8), (duplicated character:1.8), (double character:1.8), (different person:1.8), (inconsistent character:1.8), (different face:1.8), (changing face:1.8), (morphing face:1.8)"
        else:
            negative_text = f"{base_negative}, {scene_negative}"
            
        print(f"Negative Prompt: {negative_text}")
        print(f"Seed: {scene_seed}")
        print(f"Steps: {steps}, CFG Scale: {cfg_scale}")
        print(f"Sampler: {sampler}")

        # Positive prompt encoding
        workflow[str(node_id)] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": full_prompt
            }
        }
        positive_node = node_id
        node_id += 1

        # Negative prompt encoding
        workflow[str(node_id)] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": negative_text
            }
        }
        negative_node = node_id
        node_id += 1

        # KSampler
        workflow[str(node_id)] = {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale,
                "denoise": 1,
                "latent_image": ["2", 0],
                "model": ["1", 0],
                "negative": [str(negative_node), 0],
                "positive": [str(positive_node), 0],
                "sampler_name": sampler,
                "scheduler": "normal",
                "seed": scene_seed,
                "steps": steps
            }
        }
        sampler_node = node_id
        node_id += 1

        # VAE Decode
        workflow[str(node_id)] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [str(sampler_node), 0], "vae": ["1", 2]}
        }
        vae_node = node_id
        node_id += 1

        # Save Image
        formatted_seq = format_sequence_number(sequence_number)
        filename = f"scene_{formatted_seq}_{scene_type}"
        
        workflow[str(node_id)] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"{output_folder}/{filename}",
                "images": [str(vae_node), 0]
            }
        }
        output_nodes.append(node_id)
        node_id += 1

    return workflow

def build_video_workflow(image_path, clip_action, output_folder, clip_duration=3.0625, transition_type="none"):
    """Constructs the ComfyUI workflow for video generation."""
    # Calculate frames based on duration + 1 second buffer
    FPS = 16
    buffered_duration = clip_duration  # Remove the buffer to reduce memory usage
    num_frames = int(buffered_duration * FPS)
    
    # Get the base filename without extension
    base_filename = os.path.splitext(os.path.basename(image_path))[0]
    
    # Define prompts
    positive_prompt = clip_action
    negative_prompt = "distorted face, distorted hands, warping, glitching, jittering, duplicated features, melting face, morphing, unnatural movement"
    
    # Log the prompts and timing
    print("\n🎬 Video Generation Prompts:")
    print(f"Positive Prompt: {positive_prompt}")
    print(f"Negative Prompt: {negative_prompt}")
    print(f"Duration: {clip_duration}s")
    print(f"Total Frames: {num_frames}")
    
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
                "force_offload": True,  # Enable force offload to manage memory
                "clip": ["20", 0]
            },
            "class_type": "CogVideoTextEncode"
        },
        "31": {
            "inputs": {
                "prompt": negative_prompt,
                "strength": 1,
                "force_offload": True,  # Enable force offload to manage memory
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
                "crf": 5,
                "save_metadata": True,
                "trim_to_audio": False,
                "pingpong": False,
                "save_output": True,
                "save_frames": False,
                "images": ["60", 0]  # Changed from 65 to 60 to remove RIFE
            },
            "class_type": "VHS_VideoCombine"
        },
        "59": {
            "inputs": {
                "model": "kijai/CogVideoX-5b-1.5-I2V",
                "precision": "bf16",  # Use bf16 for better memory efficiency
                "quantization": "enabled",  # Enable quantization
                "enable_sequential_cpu_offload": True,  # Enable CPU offload
                "attention_mode": "sdpa",
                "load_device": "cpu"  # Load model to CPU first
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
                "enable_tiling": True,  # Enable tiling for image encode
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
                "num_frames": num_frames,
                "steps": 25,
                "cfg": 7.5,
                "seed": 546940048491023,
                "scheduler": "CogVideoXDDIM",
                "denoise_strength": 1.0,
                "model": ["59", 0],
                "positive": ["30", 0],
                "negative": ["31", 0],
                "image_cond_latents": ["62", 0]
            },
            "class_type": "CogVideoSampler"
        }
    }
    
    return workflow

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

def process_images_to_video(output_folder, sequence_data):
    """Process all generated images through the video workflow."""
    image_files = sorted([f for f in glob.glob(os.path.join(output_folder, "scene_*_*.png")) 
                         if not f.endswith('_00001.png')], 
                        key=lambda x: int(x.split('_')[1]))
    
    if not image_files:
        raise Exception("No images found in output folder")
    
    for i, (image_path, scene_data) in enumerate(zip(image_files, sequence_data)):
        print(f"\n🎥 Processing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        # Get clip parameters with validation
        clip_action = scene_data.get("clip_action", "")
        clip_duration = scene_data.get("clip_duration", 3.0625)
        
        # Validate clip duration
        if clip_duration < 1.5:
            print(f"⚠️ Warning: Clip duration {clip_duration}s is below minimum. Using 1.5s")
            clip_duration = 1.5
        elif clip_duration > 6.0:
            print(f"⚠️ Warning: Clip duration {clip_duration}s is above maximum. Using 6.0s")
            clip_duration = 6.0
            
        # Adjust duration based on shot type for optimal quality
        shot_type = scene_data.get("type", "character")
        if shot_type == "character" and clip_duration > 3.0:
            print(f"⚠️ Note: Reducing character shot duration from {clip_duration}s to 3.0s for better face consistency")
            clip_duration = 3.0
        
        transition_type = "dissolve" if i > 0 else "none"
        
        if not clip_action:
            print(f"Warning: No clip_action provided for image {image_path}, skipping...")
            continue
        
        video_workflow = build_video_workflow(
            image_path,
            clip_action,
            output_folder,
            clip_duration=clip_duration,
            transition_type=transition_type
        )
        
        try:
            print(f"Starting video generation for {os.path.basename(image_path)}...")
            print(f"Settings: FPS=16, Duration={clip_duration}s, Frames={int(clip_duration * 16)}")
            print(f"Transition: {transition_type}")
            
            p = {"prompt": video_workflow}
            req = url_request.Request(f"{COMFYUI_API_URL}/prompt", data=json.dumps(p).encode("utf-8"),
                                    headers={"Content-Type": "application/json"}, method="POST")
            
            print("Sending request to ComfyUI API...")
            response = url_request.urlopen(req)
            response_data = response.read().decode('utf-8')
            print("Response:", response_data)
            
            if not check_video(output_folder, os.path.basename(image_path)):
                print(f"❌ Failed to generate video for {os.path.basename(image_path)}")
                continue
                
            print(f"✅ Successfully processed {os.path.basename(image_path)}")
            
            # Clean up duplicates
            cleanup_pattern = os.path.join(output_folder, f"{os.path.basename(image_path).split('.')[0]}_*.png")
            for duplicate in glob.glob(cleanup_pattern):
                if duplicate != image_path:
                    try:
                        os.remove(duplicate)
                        print(f"Removed duplicate image: {os.path.basename(duplicate)}")
                    except Exception as e:
                        print(f"Failed to remove duplicate {os.path.basename(duplicate)}: {str(e)}")
            
        except Exception as e:
            print(f"❌ Error processing {image_path}: {str(e)}")
            continue

def merge_video_audio(video_path, audio_path, output_path):
    """Merge video with audio, handling duration mismatches intelligently."""
    try:
        # Get durations
        video_duration = get_media_duration(video_path)
        audio_duration = get_media_duration(audio_path)
        
        if video_duration is None or audio_duration is None:
            print("❌ Failed to get media durations")
            return False
            
        print(f"\n🎬 Merging video and audio:")
        print(f"Video duration: {video_duration:.2f}s")
        print(f"Audio duration: {audio_duration:.2f}s")
        
        # Calculate duration difference
        duration_diff = abs(video_duration - audio_duration)
        
        if duration_diff <= DURATION_TOLERANCE:
            # Durations are close enough, just merge normally
            print("Durations match within tolerance, merging normally")
            merge_cmd = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac -b:a 192k {output_path}"
        elif video_duration > audio_duration:
            # Video is longer, add silence padding to audio
            print(f"Video is longer by {duration_diff:.2f}s, adding silence padding")
            merge_cmd = f"ffmpeg -i {video_path} -i {audio_path} -filter_complex '[1:a]apad[a1]' -map 0:v -map '[a1]' -c:v copy -c:a aac -b:a 192k -shortest {output_path}"
        else:
            # Audio is longer, use -shortest to cut it
            print(f"Audio is longer by {duration_diff:.2f}s, using -shortest flag")
            merge_cmd = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac -b:a 192k -shortest {output_path}"
        
        print(f"Executing merge command: {merge_cmd}")
        result = subprocess.run(merge_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Verify the merged file
            if validate_media_file(output_path, "video"):
                print(f"✅ Successfully merged video and audio: {os.path.basename(output_path)}")
                return True
            else:
                print("❌ Merged file validation failed")
                return False
        else:
            print(f"❌ Merge command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error merging video and audio: {str(e)}")
        return False

def concatenate_videos(output_folder, max_retries=3):
    """Concatenate all video files in the output folder with retry mechanism."""
    for attempt in range(max_retries):
        try:
            print(f"\n🎬 Starting video concatenation (Attempt {attempt + 1}/{max_retries})...")
            
            # Get all final videos (either merged or original)
            video_files = sorted([
                f for f in glob.glob(os.path.join(output_folder, "scene_*_*_final.mp4")) or 
                glob.glob(os.path.join(output_folder, "scene_*_*.mp4"))
            ])
            
            if not video_files:
                print("❌ No video files found to concatenate")
                return False
            
            print(f"Found {len(video_files)} video files to process")
            
            # Create file list for concatenation
            list_file = os.path.join(output_folder, "file_list.txt")
            with open(list_file, 'w') as f:
                for video_file in video_files:
                    f.write(f"file '{os.path.basename(video_file)}'\n")
            
            # Concatenate all videos with audio
            output_file = os.path.join(output_folder, "final_video.mp4")
            
            # Use a more robust ffmpeg command that re-encodes the video
            cmd = f"ffmpeg -y -f concat -safe 0 -i {list_file} -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k -vsync 2 {output_file}"
            
            print(f"\nExecuting ffmpeg command: {cmd}")
            
            # Use subprocess to better handle the process and its output
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor the process with a timeout
            timeout = 3600  # 1 hour timeout
            start_time = time.time()
            
            while process.poll() is None:
                if time.time() - start_time > timeout:
                    process.terminate()
                    print("❌ Video concatenation timed out after 1 hour")
                    break
                time.sleep(5)  # Check every 5 seconds
                
            # Get the output and error messages
            stdout, stderr = process.communicate()
            
            # Clean up temporary files
            if os.path.exists(list_file):
                os.remove(list_file)
            
            if process.returncode == 0:
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ Successfully created final video: {output_file}")
                    print(f"Final video size: {file_size/1024/1024:.2f} MB")
                    return True
                else:
                    print("❌ Output file not created")
            else:
                print("❌ Error during video concatenation")
                print(f"FFmpeg error output: {stderr}")
            
            # If we get here, the attempt failed
            if attempt < max_retries - 1:
                print(f"\n🔄 Retrying concatenation in 10 seconds...")
                time.sleep(10)
            else:
                print("\n❌ All concatenation attempts failed")
                return False
                
        except Exception as e:
            print(f"❌ Error during video concatenation: {str(e)}")
            if attempt < max_retries - 1:
                print(f"\n🔄 Retrying concatenation in 10 seconds...")
                time.sleep(10)
            else:
                return False
                
    return False

def estimate_text_duration(text):
    """Estimate the duration of text based on average speaking rate."""
    # Average speaking rate is about 150 words per minute
    # This means each word takes about 0.4 seconds
    words = len(text.split())
    estimated_duration = words * 0.4
    return estimated_duration

def adjust_text_for_duration(text, target_duration):
    """Adjust text to fit within target duration."""
    current_duration = estimate_text_duration(text)
    if current_duration <= target_duration:
        return text
        
    # If text is too long, try to make it more concise
    words = text.split()
    target_words = int(target_duration / 0.4)  # 0.4 seconds per word
    if target_words < 3:  # Minimum 3 words for coherence
        target_words = 3
        
    # Keep the most important words (start and end)
    if len(words) > target_words:
        kept_words = words[:target_words-2] + ["..."] + words[-2:]
        return " ".join(kept_words)
    return text

def generate_narration(text, output_folder, base_filename, voice="default"):
    """Generate narration using TTS API"""
    try:
        # Ensure text is properly encoded
        encoded_text = text.encode('utf-8').decode('utf-8')
        
        # Prepare request data with filename and filepath
        data = {
            "text": encoded_text,
            "voice": voice,
            "filename": f"{base_filename}____00001_",  # Using exactly 4 underscores
            "filepath": output_folder
        }
        
        # Use ASCII-only logging
        print("\n[INFO] Generating narration:")
        print(f"[INFO] Text: {text}")
        print(f"[INFO] Voice: {voice}")
        print(f"[INFO] Output: {os.path.join(output_folder, data['filename'] + '.wav')}")
        
        # First, check if the file already exists
        audio_file = os.path.join(output_folder, data['filename'] + '.wav')
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            print(f"[SUCCESS] Audio file already exists: {audio_file}")
            file_size = os.path.getsize(audio_file)
            print(f"[INFO] File size: {file_size/1024:.2f} KB")
            return True
        
        # Send request to TTS API info endpoint first
        print("\n[INFO] Checking TTS API info...")
        info_response = requests.post(TTS_API_URL + "_info", json=data)
        
        if info_response.status_code != 200:
            print(f"[ERROR] TTS API info check failed: {info_response.text}")
            return False
            
        info_data = info_response.json()
        
        # Now send request to TTS API
        print("\n[INFO] Sending request to TTS API...")
        response = requests.post(TTS_API_URL, json=data)
        
        # Log response status only, not the full response
        print(f"[INFO] TTS API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"\n[SUCCESS] Generated narration: {data['filename']}")
            # Verify the audio file was created
            audio_file = os.path.join(output_folder, data['filename'] + '.wav')
            
            # Wait for the file to be created (with timeout)
            max_wait_time = 30  # seconds
            wait_interval = 1  # seconds
            waited = 0
            
            while not os.path.exists(audio_file) and waited < max_wait_time:
                print(f"[INFO] Waiting for audio file to be created... ({waited}/{max_wait_time}s)")
                time.sleep(wait_interval)
                waited += wait_interval
            
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"[SUCCESS] Audio file created: {audio_file}")
                print(f"[INFO] File size: {file_size/1024:.2f} KB")
                
                # Add a small delay after successful generation to prevent overwhelming the API
                time.sleep(2)
                
                return True
            else:
                print(f"[ERROR] Audio file not found at: {audio_file} after waiting {max_wait_time} seconds")
                return False
        else:
            print(f"\n[ERROR] Failed to generate narration:")
            print(f"[ERROR] Status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Network error during TTS API call: {str(e)}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error generating narration: {str(e)}")
        return False

def setup_detailed_logging(folder_id):
    """Set up detailed logging for video generation process"""
    log_dir = os.path.join(OUTPUT_BASE_DIR, folder_id, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"video_generation_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
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

def process_video_generation(folder_id, sequence_data):
    """Process video generation for a sequence of images."""
    output_folder = os.path.join(COMFYUI_OUTPUT_DIR, folder_id)
    
    if not sequence_data:
        print("No sequence data provided")
        return {"status": "error", "message": "No sequence data provided"}
    
    print(f"\nStarting audio-driven video generation for {len(sequence_data)} scenes...")
    print(f"Output folder: {output_folder}")
    
    # Phase 1: Generate all audio files first
    print("\n=== Phase 1: Generating All Audio Files ===")
    for item in sequence_data:
        if "voice_narration" not in item:
            continue
            
        scene_number = item.get("sequence_number")
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        
        print(f"\nGenerating audio for scene {scene_number}...")
        success = generate_narration(
            item["voice_narration"],
            output_folder,
            base_name,
            item.get("voice", "me")
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate audio for scene {scene_number}"}
    
    # Phase 2: Analyze audio durations
    print("\n=== Phase 2: Analyzing Audio Durations ===")
    duration_map = analyze_audio_durations(output_folder, sequence_data)
    if not duration_map:
        return {"status": "error", "message": "Failed to analyze audio durations"}
    
    # Phase 3: Generate videos based on audio durations
    print("\n=== Phase 3: Generating Videos ===")
    for item in sequence_data:
        scene_number = item.get("sequence_number")
        if not scene_number or scene_number not in duration_map:
            continue
            
        print(f"\nProcessing scene {scene_number}...")
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        video_file = os.path.join(output_folder, f"{base_name}__00001.mp4")
        
        # Get audio duration info
        audio_info = duration_map[scene_number]
        needs_adjustment, new_duration = should_adjust_clip_duration(audio_info)
        
        if needs_adjustment:
            print(f"Adjusting clip duration from {audio_info['base_clip_duration']:.2f}s to {new_duration:.2f}s")
        
        # Generate video with adjusted duration
        success = generate_video(
            os.path.join(output_folder, f"{base_name}.png"),
            video_file,
            new_duration,
            item.get("clip_action")
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate video for scene {scene_number}"}
    
    # Phase 4: Merge videos with audio
    print("\n=== Phase 4: Merging Videos with Audio ===")
    video_files = sorted(glob.glob(os.path.join(output_folder, "scene_*_*_00001__00001.mp4")))
    merged_videos = []
    
    for video_file in video_files:
        base_name = os.path.splitext(os.path.basename(video_file))[0].replace("__00001", "")
        audio_file = os.path.join(output_folder, f"{base_name}*.wav")
        
        # Find the actual audio file using glob
        audio_files = glob.glob(audio_file)
        if not audio_files:
            print(f"No audio file found for: {base_name}")
            merged_videos.append(video_file)
            continue
            
        # Use the first matching audio file
        actual_audio_file = audio_files[0]
        print(f"\nFound audio file for: {base_name}")
        merged_output = os.path.join(output_folder, f"{base_name}_final.mp4")
        
        # Validate both files before merging
        if not validate_media_file(video_file, "video") or not validate_media_file(actual_audio_file, "audio"):
            print(f"Skipping invalid files for scene {base_name}")
            continue
            
        success = merge_video_audio(video_file, actual_audio_file, merged_output)
        if success:
            merged_videos.append(merged_output)
    
    # Phase 5: Concatenate all scenes
    print("\n=== Phase 5: Concatenating All Scenes ===")
    success = concatenate_videos(output_folder)
    
    if success:
        return {"status": "success", "message": "Audio-driven video generation completed"}
    else:
        return {"status": "error", "message": "Failed to concatenate videos"}

def store_clip_data(sequence_data):
    """Store clip data for each sequence in a metadata file."""
    metadata = {}
    for scene in sequence_data:
        sequence_number = scene.get("sequence_number")
        if sequence_number is not None:
            metadata[sequence_number] = {
                "clip_action": scene.get("clip_action", ""),
                "clip_duration": scene.get("clip_duration", 3.0625),  # Use exact duration
                "type": scene.get("type", "character"),
                "voice_narration": scene.get("voice_narration", "")
            }
    return metadata

def get_clip_data(sequence_number):
    """Retrieve clip data for a specific sequence number."""
    if hasattr(app, 'clip_metadata') and sequence_number in app.clip_metadata:
        return app.clip_metadata[sequence_number]
    return None

@app.route("/generateImages", methods=["POST"])
def generate_images():
    """API endpoint to generate images for a sequence of shots."""
    try:
        data = request.get_json()
        if not data or "sequence" not in data or "character" not in data:
            return jsonify({"error": "Missing required fields: 'sequence' and 'character'"}), 400

        sequence_data = data["sequence"]
        character_data = data["character"]
        
        # Add sequence numbers to the scenes if not present
        for i, scene in enumerate(sequence_data):
            scene["sequence_number"] = i + 1

        # Get all parameters with defaults
        seed = data.get("seed", 546940048491023)
        sampler = data.get("sampler", "euler")
        steps = data.get("steps", 30)
        cfg_scale = data.get("cfg_scale", 8)
        global_negative_prompt = data.get("negative_prompt", None)

        output_folder = generate_unique_output_folder()
        print(f"📁 Created output folder: {output_folder}")
        
        # Generate images
        image_workflow = build_image_workflow(
            sequence_data, 
            character_data, 
            seed, 
            sampler, 
            steps, 
            cfg_scale,
            output_folder,
            global_negative_prompt
        )

        # Execute image generation workflow
        print("🚀 Starting image generation workflow...")
        p = {"prompt": image_workflow}
        req = url_request.Request(f"{COMFYUI_API_URL}/prompt", data=json.dumps(p).encode("utf-8"),
                                headers={"Content-Type": "application/json"}, method="POST")
        url_request.urlopen(req)

        # Wait for all images to be generated
        if not wait_for_images(output_folder, len(sequence_data)):
            return jsonify({
                "error": "Timeout waiting for image generation",
                "output_folder": output_folder,
                "generated_images": len(glob.glob(os.path.join(output_folder, "scene_*_*.png"))),
                "expected_images": len(sequence_data)
            }), 500

        return jsonify({
            "message": "✅ Image generation completed successfully!",
            "output_folder": output_folder,
            "folder_id": os.path.basename(output_folder),
            "total_scenes": len(sequence_data),
            "parameters": {
                "seed": seed,
                "sampler": sampler,
                "steps": steps,
                "cfg_scale": cfg_scale
            }
        }), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": f"❌ Error: {str(e)}"}), 500

@app.route("/generateVideos/<folder_id>", methods=["POST"])
def generate_videos(folder_id):
    try:
        data = request.get_json()
        if not data or "sequence" not in data:
            return jsonify({"status": "error", "message": "No sequence data provided"}), 400
            
        # Set up detailed logging
        logger = setup_detailed_logging(folder_id)
        logger.info(f"Starting video generation for folder: {folder_id}")
        
        # Process videos with detailed logging
        result = process_video_generation(folder_id, data["sequence"])
        
        # Log final statistics
        logger.info("Video generation process completed")
        logger.info(f"Final result: {result}")
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in video generation: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_video(image_path, output_path, duration, clip_action=None):
    """Generate a video from an image with specified duration and action."""
    try:
        # Calculate frames based on duration and FPS
        total_frames = int(duration * FPS)
        if total_frames > 1024:
            print("[WARNING] Requested {} frames exceeds maximum of 1024".format(total_frames))
            total_frames = 1024
            duration = total_frames / FPS
            print("  Adjusted to {} frames ({:.2f}s)".format(total_frames, duration))
        
        # Build the workflow with correct parameter order
        workflow = build_video_workflow(
            image_path=image_path,
            clip_action=clip_action,
            output_folder=os.path.dirname(output_path),
            clip_duration=duration
        )
        
        # Send to ComfyUI
        print("\nSending request to ComfyUI API...")
        response = requests.post(f"{COMFYUI_API_URL}/prompt", json={"prompt": workflow})
        if response.status_code != 200:
            print("[ERROR] Failed to send prompt: {}".format(response.text))
            return False
            
        prompt_id = response.json()["prompt_id"]
        print("Prompt ID: {}".format(prompt_id))
        
        # Wait for completion with better progress tracking
        print("\nWaiting for video generation to complete...")
        start_time = time.time()
        last_progress = -1
        max_wait_time = 300  # 5 minutes maximum wait time
        
        while time.time() - start_time < max_wait_time:
            # Check history for completion first
            history_response = requests.get(f"{COMFYUI_API_URL}/history")
            if history_response.status_code == 200:
                history_data = history_response.json()
                if prompt_id in history_data:
                    execution_data = history_data[prompt_id]
                    if "error" in execution_data:
                        print("[ERROR] Error during execution: {}".format(execution_data["error"]))
                        return False
                    if "outputs" in execution_data:
                        print("[SUCCESS] Video generation completed!")
                        return True
            
            # Check queue status
            queue_response = requests.get(f"{COMFYUI_API_URL}/queue")
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                if "queue_running" in queue_data and queue_data["queue_running"]:
                    current_job = queue_data["queue_running"][0]
                    if "progress" in current_job:
                        progress = current_job["progress"]
                        if progress != last_progress:
                            print("Progress: {}%".format(progress))
                            last_progress = progress
            
            time.sleep(4)  # Check every 4 seconds
            
        print("[ERROR] Timeout after {} seconds".format(max_wait_time))
        return False
        
    except Exception as e:
        print("[ERROR] Error generating video: {}".format(str(e)))
        return False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 