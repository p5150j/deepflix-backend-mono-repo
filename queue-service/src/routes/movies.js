const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const { FirebaseService } = require('../services/firebase');
const { getQueues } = require('../queues');

// Get queue instance
const { movieCreationQueue } = getQueues();

// Create a new movie
router.post('/', async (req, res) => {
  try {
    const {
      prompt,
      genre,
      num_sequences,
      seed,
      sampler,
      steps,
      cfg_scale,
      userId
    } = req.body;

    // Generate movie ID
    const movieId = uuidv4();

    // Create movie in Firebase
    const movieData = {
      id: movieId,
      prompt,
      genre,
      num_sequences,
      seed,
      sampler,
      steps,
      cfg_scale,
      userId,
      status: 'queued',
      progress: {
        story: 'pending',
        images: 'pending',
        video: 'pending'
      },
      createdAt: new Date(),
      updatedAt: new Date()
    };

    await FirebaseService.createMovie(movieData);

    // Add to movie creation queue
    const job = await movieCreationQueue.add('create-movie', {
      movieData,
      timestamp: new Date().toISOString()
    });

    res.status(201).json({
      success: true,
      movieId,
      jobId: job.id,
      status: 'queued',
      createdAt: movieData.createdAt
    });
  } catch (error) {
    console.error('Error creating movie:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create movie',
      details: error.message
    });
  }
});

// Get movie status
router.get('/:movieId/status', async (req, res) => {
  try {
    const { movieId } = req.params;
    const movie = await FirebaseService.getMovieById(movieId);

    if (!movie) {
      return res.status(404).json({
        success: false,
        error: 'Movie not found'
      });
    }

    res.json({
      success: true,
      movieId,
      status: movie.status,
      progress: movie.progress || {
        story: 'pending',
        images: 'pending',
        video: 'pending'
      },
      error: movie.error,
      updatedAt: movie.updatedAt
    });
  } catch (error) {
    console.error('Error getting movie status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get movie status',
      details: error.message
    });
  }
});

// Get movie details
router.get('/:movieId', async (req, res) => {
  try {
    const { movieId } = req.params;
    const movie = await FirebaseService.getMovieById(movieId);

    if (!movie) {
      return res.status(404).json({
        success: false,
        error: 'Movie not found'
      });
    }

    res.json({
      success: true,
      movie
    });
  } catch (error) {
    console.error('Error getting movie details:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get movie details',
      details: error.message
    });
  }
});

// Cancel movie generation
router.post('/:movieId/cancel', async (req, res) => {
  try {
    const { movieId } = req.params;
    const movie = await FirebaseService.getMovieById(movieId);

    if (!movie) {
      return res.status(404).json({
        success: false,
        error: 'Movie not found'
      });
    }

    // Update movie status
    await FirebaseService.updateMovie(movieId, {
      status: 'cancelled',
      error: 'Cancelled by user',
      updatedAt: new Date()
    });

    // Remove job from queue if it's still queued
    const waitingJobs = await movieCreationQueue.getWaiting();
    const job = waitingJobs.find(j => j.data.movieData.id === movieId);
    
    if (job) {
      await job.remove();
    }

    res.json({
      success: true,
      movieId,
      status: 'cancelled',
      cancelledAt: new Date()
    });
  } catch (error) {
    console.error('Error cancelling movie:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to cancel movie',
      details: error.message
    });
  }
});

module.exports = router; 