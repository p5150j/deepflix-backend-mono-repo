import os
import time
import subprocess
import requests
import logging
import random

TTS_API_URL = "http://localhost:5010/generate-voice"

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

def select_voice(character_data=None):
    """Select a voice based on character gender and maintain consistency."""
    voice = "me"  # Default voice
    if character_data and "base_traits" in character_data:
        base_traits = character_data["base_traits"].lower()
        print(f"\n🔍 Analyzing character traits: {base_traits}")
        
        # Define gender indicators
        female_indicators = ["woman", "female", "girl", "lady", "she", "her"]
        male_indicators = ["man", "male", "boy", "gentleman", "he", "him"]
        
        # Check for gender indicators
        is_female = any(indicator in base_traits for indicator in female_indicators)
        is_male = any(indicator in base_traits for indicator in male_indicators)
        
        if is_female:
            # Randomly select from female voices
            female_voices = ["female1", "female2", "female3"]
            voice = random.choice(female_voices)
            print(f"🎙️ Selected female voice: {voice}")
        elif is_male:
            # Randomly select from male voices
            male_voices = ["male1", "male2", "male3"]
            voice = random.choice(male_voices)
            print(f"🎙️ Selected male voice: {voice}")
        else:
            print("⚠️ Could not determine gender from base_traits, using default voice")
    
    return voice

def generate_narration(text, image_path, output_folder, logger, character_data=None, selected_voice=None):
    """Generate narration audio using TTS API with consistent voice selection"""
    try:
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        
        # Check if text is empty or just "..."
        if not text or text.strip() == "...":
            logger.info("Creating silent audio file for empty narration")
            # Get video duration to match silent audio length
            video_file = os.path.join(output_folder, f"{base_filename}_00001.mp4")
            audio_file = os.path.join(output_folder, f"{base_filename}_00001.wav")
            
            if os.path.exists(video_file):
                # Get video duration
                cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", video_file
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                duration = float(result.stdout.strip())
                
                # Create silent audio file with same properties as TTS audio
                cmd = [
                    "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=r=22050:cl=mono",
                    "-t", str(duration), "-acodec", "pcm_s16le", "-ar", "22050", "-b:a", "352800", audio_file
                ]
                subprocess.run(cmd, check=True)
                logger.info(f"Created silent audio file: {audio_file}")
                time.sleep(1)  # Add delay after file creation
                return True, "audio_generated"
            else:
                logger.warning(f"Video file not found: {video_file}")
                return False, "video_not_found"
        
        # Use the selected voice if provided, otherwise select a new one
        voice = selected_voice if selected_voice else select_voice(character_data)
        
        # For TTS API, we need 2 underscores total (base has 1, we add 1)
        filename = f"{base_filename}_00001_"  # Using 1 underscore since base has one
        
        # For actual TTS generation, use 2 underscores to match video pattern
        data = {
            "text": text,
            "voice": voice,
            "filename": filename,
            "filepath": output_folder
        }
        
        audio_file = os.path.join(output_folder, data['filename'] + '.wav')
        
        # Rest of the existing TTS API code...
        print(f"\n🎙️ Generating narration:")
        print(f"Text: {text}")
        print(f"Voice: {voice}")
        print(f"Output: {os.path.join(output_folder, data['filename'] + '.wav')}")
        
        # First, check if the file already exists
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            print(f"✅ Audio file already exists: {audio_file}")
            file_size = os.path.getsize(audio_file)
            print(f"File size: {file_size/1024:.2f} KB")
            time.sleep(1)  # Add delay after file check
            return True, "audio_generated"
        
        # Send request to TTS API info endpoint first
        print("\nChecking TTS API info...")
        info_response = requests.post(TTS_API_URL, json=data)
        time.sleep(2)  # Add delay after API call
        
        if info_response.status_code != 200:
            print(f"❌ TTS API info check failed: {info_response.text}")
            return False, "tts_info_check_failed"
            
        # Now send request to TTS API
        print("\nSending request to TTS API...")
        response = requests.post(TTS_API_URL, json=data)
        time.sleep(2)  # Add delay after API call
        
        if response.status_code == 200:
            print(f"\n✅ Generated narration: {data['filename']}")
            # Verify the audio file was created
            audio_file = os.path.join(output_folder, data['filename'] + '.wav')
            
            # Wait for the file to be created (with timeout)
            max_wait_time = 30  # seconds
            wait_interval = 1  # seconds
            waited = 0
            
            while not os.path.exists(audio_file) and waited < max_wait_time:
                print(f"Waiting for audio file to be created... ({waited}/{max_wait_time}s)")
                time.sleep(wait_interval)
                waited += wait_interval
            
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"Audio file created: {audio_file}")
                print(f"File size: {file_size/1024:.2f} KB")
                
                # Add a small delay after successful generation to prevent overwhelming the API
                time.sleep(3)  # Increased delay after successful generation
                
                return True, "audio_generated"
            else:
                print(f"❌ Audio file not found at: {audio_file} after waiting {max_wait_time} seconds")
                return False, "audio_file_not_found"
        else:
            print(f"\n❌ Failed to generate narration:")
            print(f"Error: {response.text}")
            return False, "tts_generation_failed"
            
    except Exception as e:
        print(f"❌ Error generating narration: {str(e)}")
        return False, str(e) 