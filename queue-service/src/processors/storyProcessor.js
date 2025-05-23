const { FirebaseService } = require('../services/firebase');
const axios = require('axios');
const { Worker } = require('bullmq');

function initializeStoryProcessor(storyQueue) {
  const worker = new Worker('story-generation', async (job) => {
    console.log('📝 Processing story generation job:', {
      jobId: job.id,
      movieId: job.data.movieData.id,
      timestamp: new Date().toISOString()
    });

    try {
      // Call story generation API
      const response = await axios.post(process.env.STORY_GENERATION_API_URL, {
        prompt: job.data.movieData.prompt,
        genre: job.data.movieData.genre,
        num_sequences: job.data.movieData.num_sequences
      });

      const storyData = response.data;
      console.log('Story generation response:', storyData);

      // Update movie with story progress and data
      await FirebaseService.updateMovie(job.data.movieData.id, {
        story: storyData,
        'progress.story': 'completed',
        updatedAt: new Date()
      });

      console.log('✅ Story generation completed for movie:', job.data.movieData.id);
      
      // Return the story data for the next step
      return {
        status: 'completed',
        data: storyData
      };
    } catch (error) {
      console.error('❌ Error in story generation:', {
        movieId: job.data.movieData.id,
        error: error.message,
        stack: error.stack,
        jobId: job.id
      });

      // Update movie with story error
      await FirebaseService.updateMovie(job.data.movieData.id, {
        'progress.story': 'failed',
        'errors.story': error.message,
        updatedAt: new Date()
      });

      throw error;
    }
  }, {
    connection: storyQueue.opts.connection,
    concurrency: 1
  });

  worker.on('error', (error) => {
    console.error('Story worker error:', error);
  });

  worker.on('completed', (job) => {
    console.log('Story job completed:', job.id);
  });

  worker.on('failed', (job, error) => {
    console.error('Story job failed:', job.id, error);
  });

  return worker;
}

module.exports = { initializeStoryProcessor }; 