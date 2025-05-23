# Firebase Service

## Overview
The Firebase Service manages all interactions with Firebase services, including storage, database operations, and authentication. It provides a unified interface for Firebase operations across the application.

## Features
- File storage management
- Database operations
- Connection validation
- URL generation
- Error handling

## Configuration
```json
{
    "apiKey": "FIREBASE_API_KEY",
    "authDomain": "FIREBASE_AUTH_DOMAIN",
    "projectId": "FIREBASE_PROJECT_ID",
    "storageBucket": "FIREBASE_STORAGE_BUCKET",
    "messagingSenderId": "FIREBASE_MESSAGING_SENDER_ID",
    "appId": "FIREBASE_APP_ID",
    "measurementId": "FIREBASE_MEASUREMENT_ID",
    "databaseURL": "https://{PROJECT_ID}.firebaseio.com"
}
```

## Functions

### `validate_firebase_connections()`
Validates connections to Firebase services.
- **Returns:**
  - `bool`: Connection status
- **Checks:**
  - Storage connection
  - Firestore connection
  - Authentication status

### `upload_video_to_firebase(local_path, folder_id, filename)`
Uploads video files to Firebase Storage.
- **Parameters:**
  - `local_path` (str): Local file path
  - `folder_id` (str): Target folder ID
  - `filename` (str): Target filename
- **Returns:**
  - `tuple`: (success: bool, url: str)
- **Storage Path:**
  - `videos/{folder_id}/{filename}`

### `update_firestore_with_video_url(folder_id, video_url)`
Updates Firestore with video metadata.
- **Parameters:**
  - `folder_id` (str): Folder ID
  - `video_url` (str): Video URL
- **Returns:**
  - `bool`: Success status
- **Document Structure:**
  ```json
  {
    "videos": {
      "url": "string",
      "timestamp": "timestamp",
      "status": "string"
    }
  }
  ```

## Database Schema

### Movies Collection
```json
{
  "movies": {
    "id": "string",
    "title": "string",
    "scenes": [
      {
        "id": "string",
        "order": "number",
        "image_url": "string",
        "video_url": "string",
        "narration": "string"
      }
    ],
    "metadata": {
      "created_at": "timestamp",
      "updated_at": "timestamp",
      "status": "string"
    }
  }
}
```

## Error Handling
- Connection validation
- Upload retry mechanism
- Transaction management
- Error logging
- Rollback support

## Example Usage
```python
# Validate connections
if validate_firebase_connections():
    # Upload video
    success, url = upload_video_to_firebase(
        local_path="video.mp4",
        folder_id="movie_123",
        filename="scene_001.mp4"
    )
    
    if success:
        # Update database
        update_firestore_with_video_url(
            folder_id="movie_123",
            video_url=url
        )
```

## Dependencies
- firebase_admin: Admin SDK
- pyrebase: Firebase Python API
- os: Environment variables
- logging: Error tracking

## Security Considerations
1. Secure credential management
2. Access control implementation
3. Data validation
4. Rate limiting
5. Error message sanitization

## Best Practices
1. Always validate connections before operations
2. Implement proper error handling
3. Use transactions for critical operations
4. Monitor storage usage
5. Implement proper cleanup 