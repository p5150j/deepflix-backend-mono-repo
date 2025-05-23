import os
import time
import subprocess
import requests

MUSIC_GEN_API_URL = "http://localhost:5009/generate"

def generate_music_score(output_folder, music_score):
    """Generate background music for the final movie."""
    try:
        print("\n🎵 Generating Music Score:")
        print(f"Style: {music_score.get('style', 'N/A')}")
        print(f"Type: {music_score.get('type', 'N/A')}")
        print(f"Instrumentation: {music_score.get('instrumentation', 'N/A')}")
        print(f"Tempo: {music_score.get('tempo', 'N/A')}")
        print(f"Duration: 95 seconds")
        
        # Format music score as a string
        music_prompt = (
            f"Style: {music_score.get('style', '')}, "
            f"Type: {music_score.get('type', '')}, "
            f"Instrumentation: {music_score.get('instrumentation', '')}, "
            f"Tempo: {music_score.get('tempo', '')}"
        )
        
        # Prepare the request payload
        payload = {
            "ref_prompt": music_prompt,
            "audio_length": 95,  # Hardcoded to 95 seconds
            "repo_id": "ASLP-lab/DiffRhythm-base",
            "output_dir": output_folder,
            "chunked": True
        }
        
        # Send request to music generation server
        print("\nSending request to music generation server...")
        response = requests.post(MUSIC_GEN_API_URL, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Music generation failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        # Check for output file
        output_file = os.path.join(output_folder, "output.wav")
        max_wait_time = 300  # 5 minutes timeout
        wait_interval = 5  # Check every 5 seconds
        waited = 0
        
        print("\n⏳ Waiting for music generation to complete...")
        while not os.path.exists(output_file) and waited < max_wait_time:
            print(f"Waiting... ({waited}/{max_wait_time}s)")
            time.sleep(wait_interval)
            waited += wait_interval
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"\n✅ Music generated successfully: {output_file}")
            print(f"File size: {file_size/1024/1024:.2f} MB")
            return True
        else:
            print(f"❌ Music file not found after {max_wait_time} seconds")
            return False
            
    except Exception as e:
        print(f"❌ Error generating music: {str(e)}")
        return False

def add_background_music(output_folder):
    """Add background music to the final movie with smooth transitions."""
    try:
        print("\n=== Adding Background Music ===")
        
        # Get video duration
        input_video = os.path.join(output_folder, "final_movie.mp4")
        cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {input_video}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error getting video duration: {result.stderr}")
            return False
            
        video_duration = float(result.stdout.strip())
        print(f"Video duration: {video_duration:.2f} seconds")
        
        # Step 1: Process music file (convert to mono, match sample rate)
        print("Processing music file...")
        music_file = os.path.join(output_folder, "output.wav")
        processed_music = os.path.join(output_folder, "processed_music.wav")
        cmd = f"ffmpeg -i {music_file} -ac 1 -ar 22050 -acodec pcm_s16le {processed_music}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error processing music file: {result.stderr}")
            return False
            
        # Get music duration
        cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {processed_music}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error getting music duration: {result.stderr}")
            return False
            
        music_duration = float(result.stdout.strip())
        print(f"Music duration: {music_duration:.2f} seconds")
        
        # Calculate number of loops needed
        num_loops = int(video_duration / music_duration) + 2  # Add 2 extra loops for safety
        print(f"Number of loops needed: {num_loops}")
        
        # Step 2: Add fades to music (2-second fade in/out)
        print("Adding fades to music...")
        faded_music = os.path.join(output_folder, "faded_music.wav")
        fade_duration = min(2.0, music_duration * 0.1)  # Use 10% of music duration or 2s, whichever is smaller
        fade_out_start = music_duration - fade_duration
        cmd = f"ffmpeg -i {processed_music} -af \"afade=t=in:st=0:d={fade_duration},afade=t=out:st={fade_out_start}:d={fade_duration}\" {faded_music}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error adding fades: {result.stderr}")
            return False
            
        # Step 3: Create loop list
        print("Creating music loop...")
        music_list = os.path.join(output_folder, "music_list.txt")
        with open(music_list, 'w') as f:
            for _ in range(num_loops):
                f.write("file 'faded_music.wav'\n")
            
        # Step 4: Concatenate faded music
        looped_music = os.path.join(output_folder, "looped_music_faded.wav")
        cmd = f"ffmpeg -f concat -safe 0 -i {music_list} -c copy {looped_music}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error concatenating music: {result.stderr}")
            return False
            
        # Step 5: Final mix (combine video with music at 15% volume)
        print("Mixing music with video...")
        output_video = os.path.join(output_folder, "final_movie_with_music_smooth.mp4")
        cmd = f"ffmpeg -i {input_video} -i {looped_music} -filter_complex \"[0:a][1:a]amerge=inputs=2,pan=stereo|c0=c0+0.15*c1|c1=c0+0.15*c1[a]\" -map 0:v -map \"[a]\" -c:v copy -c:a aac -b:a 192k {output_video}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error mixing audio: {result.stderr}")
            return False
            
        # Clean up temporary files
        for temp_file in [processed_music, faded_music, music_list, looped_music]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
        print(f"✅ Successfully added background music: {output_video}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding background music: {str(e)}")
        return False 