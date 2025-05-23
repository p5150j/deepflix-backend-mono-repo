const express = require('express');
const router = express.Router();
const { getQueues } = require('../queues');

// Get queue instances
const { movieCreationQueue, storyQueue, imageQueue, videoQueue } = getQueues();

// Get queue statistics
router.get('/stats', async (req, res) => {
  try {
    // Get counts for each queue
    const [movieStats, storyStats, imageStats, videoStats] = await Promise.all([
      movieCreationQueue.getJobCounts(),
      storyQueue.getJobCounts(),
      imageQueue.getJobCounts(),
      videoQueue.getJobCounts()
    ]);

    // Calculate total jobs
    const totalJobs = {
      waiting: movieStats.waiting + storyStats.waiting + imageStats.waiting + videoStats.waiting,
      active: movieStats.active + storyStats.active + imageStats.active + videoStats.active,
      completed: movieStats.completed + storyStats.completed + imageStats.completed + videoStats.completed,
      failed: movieStats.failed + storyStats.failed + imageStats.failed + videoStats.failed,
      delayed: movieStats.delayed + storyStats.delayed + imageStats.delayed + videoStats.delayed,
      paused: movieStats.paused + storyStats.paused + imageStats.paused + videoStats.paused
    };

    // Get average wait times
    const [movieWaitTime, storyWaitTime, imageWaitTime, videoWaitTime] = await Promise.all([
      getAverageWaitTime(movieCreationQueue),
      getAverageWaitTime(storyQueue),
      getAverageWaitTime(imageQueue),
      getAverageWaitTime(videoQueue)
    ]);

    res.json({
      success: true,
      total: totalJobs,
      queues: {
        movieCreation: {
          counts: movieStats,
          averageWaitTime: movieWaitTime
        },
        story: {
          counts: storyStats,
          averageWaitTime: storyWaitTime
        },
        image: {
          counts: imageStats,
          averageWaitTime: imageWaitTime
        },
        video: {
          counts: videoStats,
          averageWaitTime: videoWaitTime
        }
      },
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Error getting queue statistics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get queue statistics',
      details: error.message
    });
  }
});

// Helper function to calculate average wait time
async function getAverageWaitTime(queue) {
  try {
    const completedJobs = await queue.getCompleted();
    if (completedJobs.length === 0) return 0;

    const waitTimes = completedJobs.map(job => {
      const processedAt = job.processedOn;
      const finishedAt = job.finishedOn;
      return finishedAt - processedAt;
    });

    const averageWaitTime = waitTimes.reduce((a, b) => a + b, 0) / waitTimes.length;
    return Math.round(averageWaitTime / 1000); // Convert to seconds
  } catch (error) {
    console.error('Error calculating average wait time:', error);
    return 0;
  }
}

module.exports = router; 