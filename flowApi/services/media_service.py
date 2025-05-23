import os
import time
import subprocess
import glob

def merge_video_audio(video_path, audio_path, output_path):
    """Merge video and audio files."""
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
        time.sleep(2)  # Add delay after merge operation
        
        if result == 0:
            print(f"✅ Successfully merged video and audio: {os.path.basename(output_path)}")
            time.sleep(1)  # Add delay after successful merge
            return True
        else:
            print("❌ Failed to merge video and audio")
            return False
            
    except Exception as e:
        print(f"❌ Error merging video and audio: {str(e)}")
        return False

def concatenate_videos(output_folder):
    """Concatenate all video files in the output folder"""
    try:
        # Get all final video files
        video_files = sorted(glob.glob(os.path.join(output_folder, "*_final.mp4")))
        if not video_files:
            print("❌ No video files found to concatenate")
            return False
            
        print(f"\nFound {len(video_files)} videos to concatenate")
        for video in video_files:
            print(f"  - {os.path.basename(video)}")
            
        # Create concat list file
        concat_list = os.path.join(output_folder, "concat_list.txt")
        with open(concat_list, 'w') as f:
            for video in video_files:
                f.write(f"file '{video}'\n")
                
        # Concatenate videos with proper audio handling
        output_file = os.path.join(output_folder, "final_movie.mp4")
        cmd = f"ffmpeg -f concat -safe 0 -i {concat_list} -c copy {output_file}"
        print(f"\nConcatenating videos with command: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        time.sleep(5)  # Add significant delay after concatenation
        
        if result.returncode != 0:
            print(f"❌ Error concatenating videos: {result.stderr}")
            return False
            
        print(f"\n✅ Successfully created final movie: {output_file}")
        return True
            
    except Exception as e:
        print(f"❌ Error in concatenate_videos: {str(e)}")
        return False 