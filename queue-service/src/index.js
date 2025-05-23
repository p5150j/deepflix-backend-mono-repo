require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { createBullBoard } = require('@bull-board/api');
const { BullAdapter } = require('@bull-board/api/bullAdapter');
const { ExpressAdapter } = require('@bull-board/express');
const { getQueues } = require('./queues');
const { initializeStoryProcessor } = require('./processors/storyProcessor');
const { initializeImageProcessor } = require('./processors/imageProcessor');
const { initializeVideoProcessor } = require('./processors/videoProcessor');
const { FirebaseService } = require('./services/firebase');
const moviesRouter = require('./routes/movies');
const queueRouter = require('./routes/queue');
const { Worker } = require('bullmq');

// Get queue instances
const { 
  movieCreationQueue, 
  storyQueue, 
  imageQueue, 
  videoQueue,
  movieCreationEvents,
  storyEvents,
  imageEvents,
  videoEvents
} = getQueues();

// Set up queue processors
const storyWorker = initializeStoryProcessor(storyQueue);
const imageWorker = initializeImageProcessor(imageQueue);
const videoWorker = initializeVideoProcessor(videoQueue);

const app = express();
app.use(cors());
app.use(express.json());

// Set up queue processors
const movieCreationWorker = new Worker('movie-creation', async (job) => {
  console.log('🎬 Processing movie creation job:', {
    jobId: job.id,
    movieId: job.data.movieData.id,
    timestamp: new Date().toISOString()
  });

  try {
    // Add movie to story generation queue
    const storyJob = await storyQueue.add('generate-story', {
      movieData: job.data.movieData
    });

    // Wait for story generation to complete using QueueEvents
    const storyResult = await new Promise((resolve, reject) => {
      const onCompleted = async (completedJob) => {
        if (completedJob.jobId === storyJob.id) {
          cleanup();
          resolve(completedJob.returnvalue);
        }
      };

      const onFailed = async (failedJob, err) => {
        if (failedJob.jobId === storyJob.id) {
          cleanup();
          reject(err || new Error('Story generation failed'));
        }
      };

      const cleanup = () => {
        storyEvents.removeListener('completed', onCompleted);
        storyEvents.removeListener('failed', onFailed);
      };

      storyEvents.on('completed', onCompleted);
      storyEvents.on('failed', onFailed);
    });

    console.log('Story generation result:', storyResult);

    // Add movie to image generation queue with story data
    const imageJob = await imageQueue.add('generate-images', {
      movieData: {
        ...job.data.movieData,
        story: storyResult.data
      }
    });

    // Wait for image generation to complete using QueueEvents
    const imageResult = await new Promise((resolve, reject) => {
      const onCompleted = async (completedJob) => {
        if (completedJob.jobId === imageJob.id) {
          cleanup();
          resolve(completedJob.returnvalue);
        }
      };

      const onFailed = async (failedJob, err) => {
        if (failedJob.jobId === imageJob.id) {
          cleanup();
          reject(err || new Error('Image generation failed'));
        }
      };

      const cleanup = () => {
        imageEvents.removeListener('completed', onCompleted);
        imageEvents.removeListener('failed', onFailed);
      };

      imageEvents.on('completed', onCompleted);
      imageEvents.on('failed', onFailed);
    });

    console.log('Image generation result:', imageResult);

    // Add movie to video generation queue with story and image data
    const videoJob = await videoQueue.add('generate-video', {
      movieData: {
        ...job.data.movieData,
        story: storyResult.data,
        images: imageResult.data
      }
    });

    // Wait for video generation to complete using QueueEvents
    const videoResult = await new Promise((resolve, reject) => {
      const onCompleted = async (completedJob) => {
        if (completedJob.jobId === videoJob.id) {
          cleanup();
          resolve(completedJob.returnvalue);
        }
      };

      const onFailed = async (failedJob, err) => {
        if (failedJob.jobId === videoJob.id) {
          cleanup();
          reject(err || new Error('Video generation failed'));
        }
      };

      const cleanup = () => {
        videoEvents.removeListener('completed', onCompleted);
        videoEvents.removeListener('failed', onFailed);
      };

      videoEvents.on('completed', onCompleted);
      videoEvents.on('failed', onFailed);
    });

    console.log('Video generation result:', videoResult);

    // Update movie with final status
    await FirebaseService.updateMovie(job.data.movieData.id, {
      status: 'completed',
      updatedAt: new Date()
    });

    console.log('✅ Movie creation completed:', job.data.movieData.id);
    return { success: true };
  } catch (error) {
    console.error('❌ Error in movie creation:', {
      movieId: job.data.movieData.id,
      error: error.message,
      stack: error.stack,
      jobId: job.id
    });

    // Update movie with error
    await FirebaseService.updateMovie(job.data.movieData.id, {
      status: 'failed',
      error: error.message,
      updatedAt: new Date()
    });

    throw error;
  }
}, {
  connection: movieCreationQueue.opts.connection,
  concurrency: 1
});

movieCreationWorker.on('error', (error) => {
  console.error('Movie creation worker error:', error);
});

// Set up Bull Board
const serverAdapter = new ExpressAdapter();
serverAdapter.setBasePath('/admin/queues');

const { addQueue, removeQueue, setQueues, replaceQueues } = createBullBoard({
  queues: [
    new BullAdapter(movieCreationQueue),
    new BullAdapter(storyQueue),
    new BullAdapter(imageQueue),
    new BullAdapter(videoQueue)
  ],
  serverAdapter
});

// Routes
app.use('/api/movies', moviesRouter);
app.use('/api/queue', queueRouter);

// Bull Board UI
app.use('/admin/queues', serverAdapter.getRouter());

// Add API endpoint to get queue position
app.get('/api/queue-position/:movieId', async (req, res) => {
  try {
    const movie = await FirebaseService.getMovieById(req.params.movieId);
    if (!movie) {
      return res.status(404).json({ error: 'Movie not found' });
    }
    res.json({ queue_position: movie.queue_position });
  } catch (error) {
    console.error('Error getting queue position:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// API endpoints
app.post('/api/movies', async (req, res) => {
  try {
    const movieData = {
      id: req.body.id,
      prompt: req.body.prompt,
      genre: req.body.genre,
      num_sequences: req.body.num_sequences,
      seed: req.body.seed,
      sampler: req.body.sampler,
      steps: req.body.steps,
      cfg_scale: req.body.cfg_scale,
      userId: req.body.userId,
      status: 'queued',
      progress: {
        story: 'pending',
        images: 'pending',
        video: 'pending'
      },
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Save to Firebase
    await FirebaseService.createMovie(movieData);

    // Add to queue
    const job = await movieCreationQueue.add('create-movie', { movieData });

    res.json({
      success: true,
      jobId: job.id,
      movieId: movieData.id
    });
  } catch (error) {
    console.error('Error creating movie:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/movies/:id', async (req, res) => {
  try {
    const movie = await FirebaseService.getMovie(req.params.id);
    if (!movie) {
      return res.status(404).json({
        success: false,
        error: 'Movie not found'
      });
    }
    res.json({ success: true, movie });
  } catch (error) {
    console.error('Error getting movie:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Cleanup function
async function cleanup() {
  console.log('Cleaning up...');
  await Promise.all([
    movieCreationQueue.close(),
    storyQueue.close(),
    imageQueue.close(),
    videoQueue.close(),
    movieCreationWorker.close(),
    storyWorker.close(),
    imageWorker.close(),
    videoWorker.close()
  ]);
  process.exit(0);
}

// Handle shutdown
process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);

const PORT = process.env.PORT || 3006;
app.listen(PORT, () => {
  console.log(`🚀 Queue service running on port ${PORT}`);
  console.log(`Bull Board available at http://localhost:${PORT}/admin/queues`);
  console.log('Queues initialized:', {
    movieCreation: movieCreationQueue.name,
    story: storyQueue.name,
    image: imageQueue.name,
    video: videoQueue.name
  });
}); 