class MockApiService {
  static async generateStory(data) {
    console.log('Mock API: Generating story with data:', data);
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API delay

    return {
      id: data.id || 'mock-story-id',
      prompt: data.prompt,
      genre: data.genre,
      character: {
        name: 'Mock Character',
        description: 'A mysterious figure in the shadows'
      },
      music_score: {
        mood: 'suspenseful',
        tempo: 'moderate'
      },
      sequence: Array(data.num_sequences).fill(null).map((_, index) => ({
        id: `seq-${index}`,
        description: `Scene ${index + 1}`,
        duration: 5,
        images: []
      }))
    };
  }

  static async generateImages(data) {
    console.log('Mock API: Generating images with data:', data);
    await new Promise(resolve => setTimeout(resolve, 3000)); // Simulate API delay

    return {
      folder_id: data.folder_id,
      sequence: data.sequence.map(seq => ({
        ...seq,
        image_url: `https://mock-images.com/${data.folder_id}/${seq.id}.png`
      }))
    };
  }

  static async generateVideo(data) {
    console.log('Mock API: Generating video with data:', data);
    await new Promise(resolve => setTimeout(resolve, 4000)); // Simulate API delay

    return {
      video_url: `https://mock-videos.com/${data.folder_id}/final.mp4`,
      duration: data.sequence.length * 5 // 5 seconds per scene
    };
  }
}

module.exports = {
  MockApiService
}; 