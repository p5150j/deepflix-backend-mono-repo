const admin = require('firebase-admin');
const path = require('path');
require('dotenv').config();

// Initialize Firebase Admin with service account
const serviceAccount = require(path.resolve(process.env.FIREBASE_SERVICE_ACCOUNT_PATH));

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: `https://${serviceAccount.project_id}.firebaseio.com`,
  storageBucket: `${serviceAccount.project_id}.appspot.com`
});

// Movie status types
const MovieStatus = {
  QUEUED: 'queued',
  PROCESSING: 'processing',
  STORY_COMPLETED: 'story_completed',
  IMAGES_COMPLETED: 'images_completed',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

// Processing steps
const ProcessingStep = {
  STORY: 'story',
  IMAGES: 'images',
  VIDEO: 'video'
};

const db = admin.firestore();

class FirebaseService {
  static get db() {
    return admin.firestore();
  }

  static async createMovie(movieData) {
    try {
      const movieRef = this.db.collection('movies').doc(movieData.id);
      await movieRef.set({
        ...movieData,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
        updatedAt: admin.firestore.FieldValue.serverTimestamp()
      });
      return movieData.id;
    } catch (error) {
      console.error('Error creating movie:', error);
      throw error;
    }
  }

  static async updateMovie(movieId, updateData) {
    try {
      const movieRef = this.db.collection('movies').doc(movieId);
      await movieRef.update({
        ...updateData,
        updatedAt: admin.firestore.FieldValue.serverTimestamp()
      });
    } catch (error) {
      console.error('Error updating movie:', error);
      throw error;
    }
  }

  static async updateMovieStatus(movieId, status, step = null) {
    try {
      const movieRef = this.db.collection('movies').doc(movieId);
      const updateData = {
        status,
        updatedAt: admin.firestore.FieldValue.serverTimestamp()
      };
      
      if (step) {
        updateData.currentStep = step;
      }
      
      await movieRef.update(updateData);
    } catch (error) {
      console.error('Error updating movie status:', error);
      throw error;
    }
  }

  static async getMovieById(movieId) {
    try {
      const movieRef = this.db.collection('movies').doc(movieId);
      const movieDoc = await movieRef.get();
      
      if (!movieDoc.exists) {
        return null;
      }
      
      return movieDoc.data();
    } catch (error) {
      console.error('Error getting movie:', error);
      throw error;
    }
  }

  static async getMoviesByStatus(status) {
    const snapshot = await db.collection('movies')
      .where('status', '==', status)
      .get();
    
    return snapshot.docs.map(doc => doc.data());
  }

  static async getActiveJobs() {
    const statuses = ['queued', 'story_generating', 'images_generating', 'video_generating'];
    const snapshot = await db.collection('movies')
      .where('status', 'in', statuses)
      .get();
    
    return snapshot.docs.map(doc => doc.data());
  }
}

module.exports = {
  FirebaseService,
  MovieStatus,
  ProcessingStep,
  db
}; 