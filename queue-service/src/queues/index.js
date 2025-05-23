const { Queue, Worker, QueueEvents } = require('bullmq');
const { Redis } = require('ioredis');
require('dotenv').config();

// Create Redis connection
const connection = new Redis({
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT,
  maxRetriesPerRequest: null
});

// Initialize queues
function initializeQueues() {
  // Parent queue for movie creation
  const movieCreationQueue = new Queue('movie-creation', {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 1000,
      },
      removeOnComplete: true,
      removeOnFail: false,
    },
    limiter: {
      max: parseInt(process.env.MAX_CONCURRENT_MOVIES),
      duration: 1000,
    },
  });

  // Child queues for each step
  const storyQueue = new Queue('story-generation', {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 1000,
      },
      removeOnComplete: true,
      removeOnFail: false,
    },
  });

  const imageQueue = new Queue('image-generation', {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 1000,
      },
      removeOnComplete: true,
      removeOnFail: false,
    },
  });

  const videoQueue = new Queue('video-generation', {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 1000,
      },
      removeOnComplete: true,
      removeOnFail: false,
    },
  });

  // Set up QueueEvents for each queue
  const movieCreationEvents = new QueueEvents('movie-creation', { connection });
  const storyEvents = new QueueEvents('story-generation', { connection });
  const imageEvents = new QueueEvents('image-generation', { connection });
  const videoEvents = new QueueEvents('video-generation', { connection });

  // Set up error handling
  [movieCreationQueue, storyQueue, imageQueue, videoQueue].forEach(queue => {
    queue.on('error', (error) => {
      console.error(`Queue ${queue.name} error:`, error);
    });
  });

  // Set up event handling
  [movieCreationEvents, storyEvents, imageEvents, videoEvents].forEach(events => {
    events.on('error', (error) => {
      console.error(`QueueEvents ${events.name} error:`, error);
    });
  });

  return {
    movieCreationQueue,
    storyQueue,
    imageQueue,
    videoQueue,
    movieCreationEvents,
    storyEvents,
    imageEvents,
    videoEvents,
    connection
  };
}

// Export a singleton instance
let queues = null;
function getQueues() {
  if (!queues) {
    queues = initializeQueues();
  }
  return queues;
}

module.exports = { getQueues }; 