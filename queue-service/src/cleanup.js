const { getQueues } = require('./queues');
const { Redis } = require('ioredis');
require('dotenv').config();

async function cleanup() {
  console.log('Starting cleanup...');
  
  try {
    // Get queue instances
    const { movieCreationQueue, storyQueue, imageQueue, videoQueue, connection } = getQueues();
    
    console.log('Clearing queues...');
    await Promise.all([
      movieCreationQueue.obliterate({ force: true }),
      storyQueue.obliterate({ force: true }),
      imageQueue.obliterate({ force: true }),
      videoQueue.obliterate({ force: true })
    ]);
    
    // Clear Redis keys related to BullMQ
    console.log('Clearing Redis keys...');
    const keys = await connection.keys('bull:*');
    if (keys.length > 0) {
      await connection.del(keys);
    }
    
    console.log('Cleanup completed successfully!');
    console.log(`Cleared ${keys.length} Redis keys`);
    
  } catch (error) {
    console.error('Error during cleanup:', error);
  } finally {
    process.exit(0);
  }
}

// Run cleanup
cleanup(); 