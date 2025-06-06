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

# API Config
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_BASE_DIR = os.path.expanduser("~/Desktop/ComfyUI")
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_BASE_DIR, "output", "output")
OUTPUT_BASE_DIR = "output"

# Add TTS API URL
TTS_API_URL = "http://localhost:5005/tts"

app = Flask(__name__)

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
                "height": 1088,    # HD aspect ratio (16:9) height
                "width": 640    # HD aspect ratio (16:9) width
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
        scene_negative = scene.get("negative_prompt", "")
        base_negative = global_negative_prompt if global_negative_prompt else "(worst quality, low quality:1.4), (blurry:1.2), watermark, signature, text, logo"
        
        if scene_type == "character":
            negative_text = f"{base_negative}, {scene_negative}, (multiple people:1.8), (two women:1.8), (two persons:1.8), (twins:1.8), (multiple subjects:1.8), (group of people:1.8), (duplicated character:1.8), (double character:1.8), (different person:1.8), (inconsistent character:1.8), (different face:1.8), (changing face:1.8), (morphing face:1.8)"
        else:
            negative_text = f"{base_negative}, {scene_negative}"

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
    buffered_duration = clip_duration + 1.0  # Add 1 second buffer
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
    print(f"Original Duration: {clip_duration}s")
    print(f"Buffered Duration: {buffered_duration}s")
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
                "width": 640,
                "height": 1088,
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
        },
        "65": {                        # Added RIFE VFI node for frame interpolation
            "inputs": {
                "ckpt_name": "rife47.pth",
                "clear_cache_after_n_frames": 10,
                "multiplier": 1.5,
                "fast_mode": False,
                "ensemble": True,
                "scale_factor": 1,
                "frames": ["60", 0]
            },
            "class_type": "RIFE VFI"
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
            req = url_request.Request(COMFYUI_API_URL, data=json.dumps(p).encode("utf-8"),
                                    headers={"Content-Type": "application/json"})
            
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
    """Merge video with audio, adding padding if video is longer."""
    try:
        # First get video duration
        video_duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
        video_duration = float(os.popen(video_duration_cmd).read().strip())
        
        # Get audio duration
        audio_duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {audio_path}"
        audio_duration = float(os.popen(audio_duration_cmd).read().strip())
        
        print(f"\n🎬 Merging video and audio:")
        print(f"Video duration: {video_duration:.2f}s")
        print(f"Audio duration: {audio_duration:.2f}s")
        
        if video_duration > audio_duration:
            # If video is longer, use apad filter to add silence
            print("Video is longer than audio, adding silence padding...")
            merge_cmd = f"ffmpeg -i {video_path} -i {audio_path} -filter_complex '[1:a]apad[a1]' -map 0:v -map '[a1]' -c:v copy -c:a aac -shortest {output_path}"
        else:
            # If audio is longer or equal, just merge normally
            merge_cmd = f"ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac -shortest {output_path}"
        
        print(f"Executing merge command: {merge_cmd}")
        result = os.system(merge_cmd)
        
        if result == 0:
            print(f"✅ Successfully merged video and audio: {os.path.basename(output_path)}")
            return True
        else:
            print("❌ Failed to merge video and audio")
            return False
            
    except Exception as e:
        print(f"❌ Error merging video and audio: {str(e)}")
        return False

def concatenate_videos(output_folder):
    """Concatenate all video files in the output folder."""
    try:
        # Get all final videos (either merged or original)
        video_files = sorted([
            f for f in glob.glob(os.path.join(output_folder, "scene_*_*_final.mp4")) or 
            glob.glob(os.path.join(output_folder, "scene_*_*.mp4"))
        ])
        
        if not video_files:
            print("❌ No video files found to concatenate")
            return False
        
        print("\n🎬 Starting video concatenation...")
        print(f"Found {len(video_files)} video files to process")
        
        # Create file list for concatenation
        list_file = os.path.join(output_folder, "file_list.txt")
        with open(list_file, 'w') as f:
            for video_file in video_files:
                f.write(f"file '{os.path.basename(video_file)}'\n")
        
        # Concatenate all videos with audio
        output_file = os.path.join(output_folder, "final_video.mp4")
        cmd = f"ffmpeg -f concat -safe 0 -i {list_file} -c:v copy -c:a aac -vsync 2 {output_file}"
        
        print(f"\nExecuting ffmpeg command: {cmd}")
        result = os.system(cmd)
        
        # Clean up temporary files
        if os.path.exists(list_file):
            os.remove(list_file)
        
        if result == 0:
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"✅ Successfully created final video: {output_file}")
                print(f"Final video size: {file_size/1024:.2f} KB")
                return True
            else:
                print("❌ Output file not created")
                return False
        else:
            print("❌ Error during video concatenation")
            return False
            
    except Exception as e:
        print(f"❌ Error during video concatenation: {str(e)}")
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
        # Use 4 underscores to match the actual file pattern
        data = {
            "text": encoded_text,
            "voice": voice,
            "filename": f"{base_filename}____00001_",  # Using exactly 4 underscores
            "filepath": output_folder
        }
        
        print(f"\n🎙️ Generating narration:")
        print(f"Text: {text}")
        print(f"Voice: {voice}")
        print(f"Output: {os.path.join(output_folder, data['filename'] + '.wav')}")
        print(f"Request data: {json.dumps(data, indent=2)}")
        
        # Send request to TTS API
        print("\nSending request to TTS API...")
        response = requests.post(TTS_API_URL, json=data)
        
        # Log detailed response information
        print(f"\nTTS API Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Body (raw): {response.text}")
        
        if response.status_code == 200:
            print(f"\n✅ Generated narration: {data['filename']}")
            # Verify the audio file was created
            audio_file = os.path.join(output_folder, data['filename'] + '.wav')
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"Audio file created: {audio_file}")
                print(f"File size: {file_size/1024:.2f} KB")
                return True
            else:
                print(f"❌ Audio file not found at: {audio_file}")
                return False
        else:
            print(f"\n❌ Failed to generate narration:")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error during TTS API call: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Error generating narration: {str(e)}")
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
    """Process video generation for a sequence of images in strict sequential order."""
    output_folder = os.path.join(COMFYUI_OUTPUT_DIR, folder_id)
    
    if not sequence_data:
        print("❌ No sequence data provided")
        return {"status": "error", "message": "No sequence data provided"}
    
    print(f"\nStarting video generation for {len(sequence_data)} scenes...")
    print(f"Output folder: {output_folder}")
    
    # Phase 1: Generate all videos
    print("\n=== Phase 1: Generating Videos ===")
    for item in sequence_data:
        scene_number = item.get("sequence_number")
        if not scene_number:
            continue
            
        print(f"\nProcessing scene {scene_number}...")
        # Update the base name to match the exact pattern we see in the directory
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        video_file = os.path.join(output_folder, f"{base_name}__00001.mp4")
        
        # Generate video using the correct image pattern
        success = generate_video(
            os.path.join(output_folder, f"{base_name}.png"),
            video_file,
            item.get("clip_duration", 3.0625)
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate video for scene {scene_number}"}
    
    # Phase 2: Generate all audio
    print("\n=== Phase 2: Generating Audio ===")
    for item in sequence_data:
        if "voice_narration" not in item:
            continue
            
        scene_number = item.get("sequence_number")
        # Update the base name to match the exact pattern we see in the directory
        base_name = f"scene_{format_sequence_number(scene_number)}_{item.get('type', 'character')}_00001_"
        audio_file = os.path.join(output_folder, f"{base_name}_____00001_.wav")  # Exactly 5 underscores
        
        print(f"\nGenerating audio for scene {scene_number}...")
        success = generate_narration(
            item["voice_narration"],
            output_folder,
            base_name,
            item.get("voice", "me")
        )
        
        if not success:
            return {"status": "error", "message": f"Failed to generate audio for scene {scene_number}"}
    
    # Phase 3: Merge videos with audio
    print("\n=== Phase 3: Merging Videos with Audio ===")
    video_files = sorted(glob.glob(os.path.join(output_folder, "scene_*_*_00001__00001.mp4")))
    merged_videos = []
    
    for video_file in video_files:
        # Get the base name without the .mp4 extension and __00001 suffix
        base_name = os.path.splitext(os.path.basename(video_file))[0].replace("__00001", "")
        # Look for the audio file with exactly 5 underscores
        audio_file = os.path.join(output_folder, f"{base_name}_____00001_.wav")
        
        print(f"\nChecking for audio file: {audio_file}")
        if os.path.exists(audio_file):
            print(f"Found audio file for: {base_name}")
            merged_output = os.path.join(output_folder, f"{base_name}_final.mp4")
            success = merge_video_audio(video_file, audio_file, merged_output)
            if success:
                merged_videos.append(merged_output)
        else:
            print(f"No audio file found for: {base_name}")
            merged_videos.append(video_file)
    
    # Phase 4: Concatenate all scenes
    print("\n=== Phase 4: Concatenating All Scenes ===")
    success = concatenate_videos(output_folder)
    
    if success:
        return {"status": "success", "message": "Video generation completed"}
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
        req = url_request.Request(COMFYUI_API_URL, data=json.dumps(p).encode("utf-8"),
                                headers={"Content-Type": "application/json"})
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

def generate_video(image_path, output_path, clip_duration=5):
    """Generate a video from an image using ComfyUI."""
    try:
        # Calculate frames based on duration + 1 second buffer
        FPS = 16
        buffered_duration = clip_duration + 1.0  # Add 1 second buffer
        num_frames = int(buffered_duration * FPS)
        
        # Get the base filename without extension
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        
        # Define prompts
        positive_prompt = "cinematic shot, high quality, detailed, sharp focus"
        negative_prompt = "distorted face, distorted hands, warping, glitching, jittering, duplicated features, melting face, morphing, unnatural movement"
        
        # Log the prompts and timing
        print("\n🎬 Video Generation Settings:")
        print(f"Input image: {image_path}")
        print(f"Output path: {output_path}")
        print(f"Original Duration: {clip_duration}s")
        print(f"Buffered Duration: {buffered_duration}s")
        print(f"Total Frames: {num_frames}")
        
        # Build the workflow
        workflow = build_video_workflow(
            image_path,
            positive_prompt,
            os.path.dirname(output_path),
            clip_duration=clip_duration
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
            timeout = 600  # 10 minutes timeout
            last_progress = 0
            last_status = None
            completion_detected = False
            
            while time.time() - start_time < timeout:
                # Check queue status
                queue_response = requests.get("http://127.0.0.1:8188/queue")
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    if "queue_running" in queue_data and prompt_id in queue_data["queue_running"]:
                        current_status = "🎬 Video generation in progress..."
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
                            print(f"📊 Video file growing: {current_size/1024:.1f} KB")
                            last_progress = current_size
                            last_status = f"📊 Video file growing: {current_size/1024:.1f} KB"
                
                time.sleep(2)
            
            if not completion_detected:
                print(f"❌ Video generation timed out after {timeout} seconds")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 