# DeepFlix Queue Service API Documentation

## Base URL
```
http://localhost:3006
```

## Endpoints

### 1. Create Movie
Creates a new movie generation job and adds it to the processing queue.

**Endpoint:** `POST /api/movies`

**Request Body:**
```json
{
  "id": "string",              // Optional: Custom movie ID
  "prompt": "string",          // Required: Story prompt
  "genre": "string",           // Required: Movie genre
  "num_sequences": number,     // Required: Number of sequences
  "seed": number,             // Required: Random seed for generation
  "sampler": "string",        // Required: Sampler type (e.g., "euler")
  "steps": number,            // Required: Number of steps
  "cfg_scale": number,        // Required: CFG scale
  "userId": "string"          // Required: User ID
}
```

**Response:**
```json
{
  "success": true,
  "movieId": "string",        // Generated movie ID
  "jobId": "string",          // Job ID in the queue
  "status": "queued",
  "createdAt": "string"       // ISO timestamp
}
```

**Example:**
```bash
curl -X POST http://localhost:3006/api/movies \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cyberpunk detective story set in 2084",
    "genre": "cyberpunk",
    "num_sequences": 3,
    "seed": 391688,
    "sampler": "euler",
    "steps": 20,
    "cfg_scale": 7.5,
    "userId": "test-user-123"
  }'
```

### 2. Get Movie Status
Retrieves the current status of a movie generation job.

**Endpoint:** `GET /api/movies/:movieId/status`

**Response:**
```json
{
  "success": true,
  "movieId": "string",
  "status": "string",         // queued, processing, completed, failed
  "progress": {
    "story": "string",        // pending, processing, completed, failed
    "images": "string",       // pending, processing, completed, failed
    "video": "string"         // pending, processing, completed, failed
  },
  "updatedAt": {
    "_seconds": number,
    "_nanoseconds": number
  }
}
```

**Example:**
```bash
curl http://localhost:3006/api/movies/123e4567-e89b-12d3-a456-426614174000/status
```

### 3. Get Queue Position
Retrieves the current position of a job in the queue.

**Endpoint:** `GET /api/queue/:jobId/position`

**Response:**
```json
{
  "success": true,
  "jobId": "string",
  "position": number,         // Position in queue (0-based)
  "totalJobs": number,        // Total jobs in queue
  "estimatedWaitTime": number // Estimated wait time in seconds
}
```

**Example:**
```bash
curl http://localhost:3006/api/queue/123/position
```

## Processing Flow

1. **Movie Creation**
   - Job is added to `movieCreationQueue`
   - Processed one at a time (concurrency: 1)

2. **Story Generation**
   - Added to `storyQueue` after movie creation starts
   - Waits for completion before proceeding

3. **Image Generation**
   - Added to `imageQueue` after story generation completes
   - Waits for completion before proceeding

4. **Video Generation**
   - Added to `videoQueue` after image generation completes
   - Final step in the process

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

Error responses include:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Notes

- All timestamps are in ISO 8601 format
- Queue positions are 0-based (0 is the first position)
- Job processing is strictly sequential
- No parallel processing of different stages for the same movie
- Each movie must complete all stages before the next movie starts 