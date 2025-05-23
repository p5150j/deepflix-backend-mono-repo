const { FirebaseService } = require('../services/firebase');
const axios = require('axios');
const { Worker } = require('bullmq');

function initializeImageProcessor(imageQueue) {
  const worker = new Worker('image-generation', async (job) => {
    console.log('🎨 Processing image generation job:', {
      jobId: job.id,
      movieId: job.data.movieData.id,
      timestamp: new Date().toISOString()
    });

    try {
      // Log the story data to verify its structure
      console.log('Story data:', job.data.movieData.story);

      // Call image generation API with the complete story data
      const response = await axios.post(process.env.IMAGE_GENERATION_API_URL, {
        folder_id: job.data.movieData.id,
        character: job.data.movieData.story.character,
        music_score: job.data.movieData.story.music_score,
        sequence: job.data.movieData.story.sequence,
        seed: job.data.movieData.seed,
        sampler: job.data.movieData.sampler,
        steps: job.data.movieData.steps,
        cfg_scale: job.data.movieData.cfg_scale
      });

      // Update movie with image progress and data
      await FirebaseService.updateMovie(job.data.movieData.id, {
        images: response.data,
        'progress.images': 'completed',
        updatedAt: new Date()
      });

      console.log('✅ Image generation completed for movie:', job.data.movieData.id);
      
      // Return the image data for the next step
      return {
        status: 'completed',
        data: response.data
      };
    } catch (error) {
      console.error('❌ Error in image generation:', {
        movieId: job.data.movieData.id,
        error: error.message,
        stack: error.stack,
        jobId: job.id,
        storyData: job.data.movieData.story // Log the story data on error
      });

      // Update movie with image error
      await FirebaseService.updateMovie(job.data.movieData.id, {
        'progress.images': 'failed',
        'errors.images': error.message,
        updatedAt: new Date()
      });

      throw error;
    }
  }, {
    connection: imageQueue.opts.connection,
    concurrency: 1
  });

  worker.on('error', (error) => {
    console.error('Image worker error:', error);
  });

  worker.on('completed', (job) => {
    console.log('Image job completed:', job.id);
  });

  worker.on('failed', (job, error) => {
    console.error('Image job failed:', job.id, error);
  });

  return worker;
}

module.exports = { initializeImageProcessor }; 