const { FirebaseService } = require('../services/firebase');
const axios = require('axios');
const { Worker } = require('bullmq');

function initializeVideoProcessor(videoQueue) {
  const worker = new Worker('video-generation', async (job) => {
    console.log('🎬 Processing video generation job:', {
      jobId: job.id,
      movieId: job.data.movieData.id,
      timestamp: new Date().toISOString()
    });

    try {
      // Call video generation API
      const response = await axios.post(`${process.env.VIDEO_GENERATION_API_URL}/${job.data.movieData.id}`, {
        folder_id: job.data.movieData.id,
        character: job.data.movieData.story.character,
        music_score: job.data.movieData.story.music_score,
        sequence: job.data.movieData.story.sequence,
        image_url: job.data.movieData.images.image_url,
        seed: job.data.movieData.seed,
        sampler: job.data.movieData.sampler,
        steps: job.data.movieData.steps,
        cfg_scale: job.data.movieData.cfg_scale
      });

      // Update movie with video progress and data
      await FirebaseService.updateMovie(job.data.movieData.id, {
        video: response.data,
        'progress.video': 'completed',
        updatedAt: new Date()
      });

      console.log('✅ Video generation completed for movie:', job.data.movieData.id);
      
      // Return the video data for the next step
      return {
        status: 'completed',
        data: response.data
      };
    } catch (error) {
      console.error('❌ Error in video generation:', {
        movieId: job.data.movieData.id,
        error: error.message,
        stack: error.stack,
        jobId: job.id
      });

      // Update movie with video error
      await FirebaseService.updateMovie(job.data.movieData.id, {
        'progress.video': 'failed',
        'errors.video': error.message,
        updatedAt: new Date()
      });

      throw error;
    }
  }, {
    connection: videoQueue.opts.connection,
    concurrency: 1
  });

  worker.on('error', (error) => {
    console.error('Video worker error:', error);
  });

  worker.on('completed', (job) => {
    console.log('Video job completed:', job.id);
  });

  worker.on('failed', (job, error) => {
    console.error('Video job failed:', job.id, error);
  });

  return worker;
}

module.exports = { initializeVideoProcessor }; 