import os
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Firebase Configuration for Storage
config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}.firebaseio.com"  # Required by pyrebase for storage
}

# Initialize Firebase Storage
firebase = pyrebase.initialize_app(config)
storage = firebase.storage()

# Initialize Firebase Admin for Firestore
cred = credentials.Certificate("deepflix-cc642-firebase-adminsdk-fbsvc-140547cc0d.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def validate_firebase_connections():
    """Validate Firebase Storage and Firestore connections."""
    print("\n🔍 Validating Firebase connections...")

    # Test storage connection
    try:
        storage.child('test').get_url(None)
        print("✅ Firebase Storage connection successful")
    except Exception as e:
        print(f"❌ Firebase Storage connection failed: {str(e)}")
        raise Exception("Failed to connect to Firebase Storage")

    # Test Firestore connection
    try:
        db.collection('movies').limit(1).get()
        print("✅ Firestore connection successful")
    except Exception as e:
        print(f"❌ Firestore connection failed: {str(e)}")
        raise Exception("Failed to connect to Firestore")

    print("✅ Firebase initialization complete\n")

def upload_video_to_firebase(video_path, movie_id):
    """Upload video to Firebase Storage and return the public URL."""
    try:
        # Extract filename from path
        filename = os.path.basename(video_path)
        
        # Create storage path: movies/{movie_id}/videos/{filename}
        storage_path = f"movies/{movie_id}/videos/{filename}"
        
        # Upload the video
        print(f"\n📤 Uploading video to Firebase Storage: {storage_path}")
        storage.child(storage_path).put(video_path)
        
        # Get the public URL
        video_url = storage.child(storage_path).get_url(None)
        print(f"✅ Video uploaded successfully: {video_url}")
        
        return video_url
    except Exception as e:
        print(f"❌ Error uploading video to Firebase: {str(e)}")
        raise

def update_firestore_with_video_url(movie_id, video_url):
    """Update Firestore document with the video URL."""
    try:
        # Get the movie document reference
        movie_ref = db.collection('movies').document(movie_id)
        
        # Update the document with the video URL
        print(f"\n📝 Updating Firestore with video URL for movie: {movie_id}")
        movie_ref.update({
            'final_video': video_url,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        print("✅ Firestore updated successfully")
    except Exception as e:
        print(f"❌ Error updating Firestore: {str(e)}")
        raise 