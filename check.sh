#!/bin/bash

# Simple script to analyze video and audio files in current directory
# Focuses on duration, framerate, and other key parameters that affect sync

# Text formatting
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BOLD}Media File Analysis${NC}"
echo "------------------------"

# Create output file for detailed results
OUTPUT_FILE="media_info.txt"
> "$OUTPUT_FILE"  # Clear file if it exists

# Find all video files
VIDEO_FILES=$(find . -name "scene_*_.mp4" | sort -V)

echo -e "\n${BOLD}Analyzing $(echo "$VIDEO_FILES" | wc -l) video/audio pairs...${NC}\n"

# Define a function to extract duration
get_duration() {
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1" 2>/dev/null
}

# Header for the table
printf "%-8s %-12s %-8s %-8s %-10s %-10s %-10s\n" "Scene" "Type" "V-Dur" "A-Dur" "Diff" "FPS" "Frames"
printf "%-8s %-12s %-8s %-8s %-10s %-10s %-10s\n" "-----" "----" "-----" "-----" "----" "---" "------"

# Process each video file and its corresponding audio
for VIDEO in $VIDEO_FILES; do
    # Extract scene number
    SCENE=$(echo $VIDEO | grep -o 'scene_[0-9]*' | cut -d'_' -f2)
    
    # Extract scene type (b-roll or character)
    if [[ $VIDEO == *"b-roll"* ]]; then
        TYPE="b-roll"
    elif [[ $VIDEO == *"character"* ]]; then
        TYPE="character"
    else
        TYPE="unknown"
    fi
    
    # Find corresponding audio file
    BASE_NAME=$(basename "$VIDEO" .mp4)
    AUDIO="${BASE_NAME}__00001_.wav"
    
    # Get video duration
    VIDEO_DUR=$(get_duration "$VIDEO")
    VIDEO_DUR=$(printf "%.2f" $VIDEO_DUR)
    
    # Get audio duration
    AUDIO_DUR=$(get_duration "$AUDIO")
    AUDIO_DUR=$(printf "%.2f" $AUDIO_DUR)
    
    # Calculate difference
    DIFF=$(echo "$VIDEO_DUR - $AUDIO_DUR" | bc)
    
    # Get framerate and frame count
    FPS=$(ffprobe -v error -select_streams v -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$VIDEO" 2>/dev/null)
    if [[ $FPS == *"/"* ]]; then
        # Convert fraction to decimal
        NUM=$(echo $FPS | cut -d'/' -f1)
        DEN=$(echo $FPS | cut -d'/' -f2)
        FPS=$(echo "scale=2; $NUM / $DEN" | bc)
    fi
    
    FRAMES=$(ffprobe -v error -select_streams v -count_packets -show_entries stream=nb_read_packets -of default=noprint_wrappers=1:nokey=1 "$VIDEO" 2>/dev/null)
    
    # Highlight significant differences
    if (( $(echo "($DIFF > 0.1 || $DIFF < -0.1)" | bc -l) )); then
        DIFF_COL="${RED}$(printf "%.2f" $DIFF)${NC}"
    else
        DIFF_COL="${GREEN}$(printf "%.2f" $DIFF)${NC}"
    fi
    
    # Print to console
    printf "%-8s %-12s %-8s %-8s %-10b %-10s %-10s\n" "$SCENE" "$TYPE" "$VIDEO_DUR" "$AUDIO_DUR" "$DIFF_COL" "$FPS" "$FRAMES"
    
    # Collect detailed information for the file
    echo "==============================================" >> "$OUTPUT_FILE"
    echo "SCENE $SCENE ($TYPE)" >> "$OUTPUT_FILE"
    echo "==============================================" >> "$OUTPUT_FILE"
    echo "VIDEO: $VIDEO" >> "$OUTPUT_FILE"
    echo "AUDIO: $AUDIO" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "VIDEO INFORMATION:" >> "$OUTPUT_FILE"
    ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,duration,nb_frames -show_entries format=duration,bit_rate "$VIDEO" 2>> "$OUTPUT_FILE" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "AUDIO INFORMATION:" >> "$OUTPUT_FILE"
    ffprobe -v error -show_entries stream=codec_name,codec_type,sample_rate,channels,duration -show_entries format=duration,bit_rate "$AUDIO" 2>> "$OUTPUT_FILE" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
done

# Print summary
echo -e "\n${BOLD}Summary:${NC}"
echo "------------------------"
echo "Detailed information saved to $OUTPUT_FILE"

# Find scenes with significant sync issues
PROBLEM_SCENES=$(grep -E '\-?[0-9]\.[0-9]{2}' "$OUTPUT_FILE" | grep -v "0.00" | wc -l)
echo -e "Scenes with potential sync issues: ${YELLOW}$PROBLEM_SCENES${NC}"

echo -e "\n${BOLD}Recommended next steps:${NC}"
echo "1. Check scenes with differences > 0.1 seconds (highlighted in red)"
echo "2. Look for inconsistent framerates across videos"
echo "3. Examine if certain scene types (b-roll vs character) have consistent issues"
echo ""
echo "To fix sync in your concatenation script:"
echo "- Make sure all videos have consistent framerates"
echo "- Consider re-encoding problem videos rather than using copy"
echo "- Try '-vsync 2' with '-async 1' for better synchronization"
