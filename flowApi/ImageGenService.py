import json
import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib import request as url_request
import glob
import time
from dotenv import load_dotenv
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

# Firebase Configuration for Storage
config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}.firebaseio.com"  # Required by pyrebase for storage
}

# Initialize Firebase Storage
firebase = pyrebase.initialize_app(config)
storage = firebase.storage()

# Initialize Firebase Admin for Firestore
cred = credentials.Certificate("deepflix-cc642-firebase-adminsdk-fbsvc-140547cc0d.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Validate Firebase connectivity
print("\n🔍 Validating Firebase connections...")

# Test storage connection
try:
    storage.child('test').get_url(None)
    print("✅ Firebase Storage connection successful")
except Exception as e:
    print(f"❌ Firebase Storage connection failed: {str(e)}")
    raise Exception("Failed to connect to Firebase Storage")

# Test Firestore connection
try:
    db.collection('movies').limit(1).get()
    print("✅ Firestore connection successful")
except Exception as e:
    print(f"❌ Firestore connection failed: {str(e)}")
    raise Exception("Failed to connect to Firestore")

print("✅ Firebase initialization complete\n")

# API Config
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_BASE_DIR = os.path.expanduser("~/Desktop/ComfyUI")
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_BASE_DIR, "output", "output")
OUTPUT_BASE_DIR = "output"

app = Flask(__name__)
CORS(app)

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

def filter_duplicate_traits(character_prompt, atmosphere):
    """Remove traits from atmosphere that already exist in character_prompt and add color balance."""
    if not atmosphere:
        return ""
        
    # Split both into individual traits
    char_traits = [trait.strip() for trait in character_prompt.split(',')]
    atmos_traits = [trait.strip() for trait in atmosphere.split(',')]
    
    # Extract the core part of each trait (before the weight)
    char_cores = [trait.split(':')[0].strip('() ').lower() for trait in char_traits]
    
    # Filter atmosphere traits and moderate color intensity
    filtered_traits = []
    has_high_contrast = False
    has_intense_colors = False
    
    for trait in atmos_traits:
        # Get core part of trait (before weight)
        core = trait.split(':')[0].strip('() ').lower()
        
        # Check for high contrast or intense color terms
        if 'high contrast' in core:
            has_high_contrast = True
            # Replace high contrast with balanced contrast
            trait = trait.replace('high contrast', 'balanced contrast').replace(':1.4', ':1.2')
        elif any(color in core for color in ['green', 'blue', 'red', 'gold', 'amber', 'crimson']):
            has_intense_colors = True
            # Reduce color intensity weights
            if ':1.4' in trait:
                trait = trait.replace(':1.4', ':1.2')
            elif ':1.3' in trait:
                trait = trait.replace(':1.3', ':1.2')
        
        # Check if this core appears in any character trait
        should_keep = True
        for char_core in char_cores:
            # If there's significant overlap in the words, consider it a duplicate
            char_words = set(char_core.split())
            trait_words = set(core.split())
            overlap = len(char_words.intersection(trait_words))
            if overlap >= 2 or char_core in core or core in char_core:
                should_keep = False
                print(f"Filtered duplicate trait: {trait} (matches {char_core})")
                break
                
        if should_keep:
            filtered_traits.append(trait)
    
    # Add color balance terms if we detected intense colors
    if has_intense_colors:
        filtered_traits.append("(natural color grading:1.3)")
        filtered_traits.append("(cinematic color balance:1.3)")
        if not has_high_contrast:
            filtered_traits.append("(balanced contrast:1.2)")
    
    # Always add photographic quality terms
    filtered_traits.append("(professional photography:1.3)")
    filtered_traits.append("(natural lighting:1.2)")
    
    return ", ".join(filtered_traits)

def build_image_workflow(sequence_data, character_data, seed, sampler, steps, cfg_scale, output_folder, global_negative_prompt=None):
    """Constructs the ComfyUI workflow for image generation."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd3.5_large_fp8_scaled.safetensors"}
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
            # Remove [previous character traits] from pose
            pose = scene['pose'].replace("[previous character traits], ", "").replace("[previous character traits]", "")
            
            # Filter out duplicate traits from atmosphere
            atmosphere = scene.get('atmosphere', '')
            filtered_atmosphere = filter_duplicate_traits(character_prompt, atmosphere)
            
            # SD 3.5 works better with clean prompts without weights
            character_prompt_clean = character_prompt.replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            pose_clean = pose.replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            filtered_atmosphere_clean = filtered_atmosphere.replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            environment_clean = scene['environment'].replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            
            # Build final prompt with clean structure
            full_prompt = f"professional photograph, {environment_clean}, {character_prompt_clean}, {pose_clean}, {filtered_atmosphere_clean}"
            
            scene_seed = base_seed
        else:
            # B-roll scene: Focus on environment first, then atmosphere
            environment_clean = scene['environment'].replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            atmosphere_clean = scene.get('atmosphere', '').replace(":1.4", "").replace(":1.3", "").replace(":1.2", "")
            full_prompt = f"professional photograph, {environment_clean}, {atmosphere_clean}, cinematic composition, dramatic lighting"
            scene_seed = base_seed

        # Log the prompts for this scene
        print(f"\n🎨 Image Generation Prompts for Scene {sequence_number}:")
        print(f"Scene Type: {scene_type}")
        print(f"Positive Prompt: {full_prompt}")
        
        # Minimal negative prompt for SD 3.5 - no weights needed
        negative_text = "cartoon, anime, illustration, drawing, painting, sketch, disfigured, deformed, extra limbs"
            
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

        # KSampler - Use input parameters instead of hardcoded values
        workflow[str(node_id)] = {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale,
                "denoise": 1,
                "latent_image": ["2", 0],
                "model": ["1", 0],
                "negative": [str(negative_node), 0],
                "positive": [str(positive_node), 0],
                "sampler_name": sampler,  # Use the input sampler
                "scheduler": "normal",    # Keep karras scheduler for better detail
                "seed": scene_seed,
                "steps": steps           # Use the input steps
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

def upload_image_to_firebase(local_path, folder_id, filename):
    """Upload an image to Firebase Storage and return its public URL."""
    try:
        # Upload the file
        storage_path = f"{folder_id}/images/{filename}"
        storage.child(storage_path).put(local_path)
        
        # Get the download URL
        url = storage.child(storage_path).get_url(None)
        return url
    except Exception as e:
        print(f"❌ Error uploading {filename} to Firebase: {str(e)}")
        return None

def update_firestore_with_urls(folder_id, image_urls):
    """Update Firestore document with image URLs."""
    try:
        # Get the movie document
        doc_ref = db.collection('movies').document(folder_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"❌ No movie found with ID: {folder_id}")
            return False
            
        # Get current data
        movie_data = doc.to_dict()
        
        # Update sequence items with image URLs
        for i, scene in enumerate(movie_data['sequence']):
            if i < len(image_urls):
                scene['image_url'] = image_urls[i]
        
        # Update the document
        doc_ref.update({
            'sequence': movie_data['sequence']
        })
        print("✅ Firestore updated with image URLs")
        return True
    except Exception as e:
        print(f"❌ Error updating Firestore: {str(e)}")
        return False

@app.route("/generateImages", methods=["POST"])
def generate_images():
    """API endpoint to generate images for a sequence of shots."""
    try:
        data = request.get_json()
        
        # Debug: Print incoming JSON structure
        print("\n📥 Incoming JSON Structure:")
        print(json.dumps(data, indent=2))
        
        # Validate required fields
        if not data or "sequence" not in data or "character" not in data or "folder_id" not in data:
            return jsonify({"error": "Missing required fields: 'sequence', 'character', and 'folder_id'"}), 400

        # Extract folder_id and create output path
        folder_id = data["folder_id"]
        output_folder = os.path.join(COMFYUI_OUTPUT_DIR, folder_id)
        
        # Debug: Print folder information
        print(f"\n📁 Folder Information:")
        print(f"Folder ID: {folder_id}")
        print(f"Output Path: {output_folder}")
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
        if not os.path.exists(output_folder):
            return jsonify({"error": f"Failed to create output folder: {output_folder}"}), 500
            
        print(f"✅ Output folder created/verified: {output_folder}")

        sequence_data = data["sequence"]
        character_data = data["character"]
        
        # Add sequence numbers to the scenes if not present
        for i, scene in enumerate(sequence_data):
            scene["sequence_number"] = i + 1

        # Get all parameters with defaults
        seed = data.get("seed", 546940048491023)
        sampler = data.get("sampler", "dpmpp_2m_sde")
        steps = data.get("steps", 30)
        cfg_scale = data.get("cfg_scale", 7.0)
        global_negative_prompt = data.get("negative_prompt", None)
        
        # Debug: Print generation parameters
        print("\n⚙️ Generation Parameters:")
        print(f"Seed: {seed}")
        print(f"Sampler: {sampler}")
        print(f"Steps: {steps}")
        print(f"CFG Scale: {cfg_scale}")
        
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
        
        # Debug: Print workflow being sent to ComfyUI
        print("\n🚀 Sending workflow to ComfyUI...")
        print(f"API URL: {COMFYUI_API_URL}")
        print(f"Total scenes: {len(sequence_data)}")

        # Execute image generation workflow
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

        # Upload images to Firebase Storage
        print("\n📤 Uploading images to Firebase Storage...")
        image_urls = []
        for i, scene in enumerate(sequence_data):
            formatted_seq = format_sequence_number(scene["sequence_number"])
            scene_type = scene["type"]
            filename = f"scene_{formatted_seq}_{scene_type}_00001_.png"
            local_path = os.path.join(output_folder, filename)
            
            if os.path.exists(local_path):
                url = upload_image_to_firebase(local_path, folder_id, filename)
                if url:
                    image_urls.append(url)
                    print(f"✅ Uploaded {filename}")
                else:
                    print(f"❌ Failed to upload {filename}")
            else:
                print(f"❌ File not found: {filename}")

        # Update Firestore with image URLs
        print("\n💾 Updating Firestore with image URLs...")
        if not update_firestore_with_urls(folder_id, image_urls):
            print("❌ Failed to update Firestore with image URLs")

        return jsonify({
            "message": "✅ Image generation and upload completed successfully!",
            "output_folder": output_folder,
            "folder_id": folder_id,
            "total_scenes": len(sequence_data),
            "image_urls": image_urls,
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 