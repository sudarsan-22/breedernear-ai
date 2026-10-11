// Where the API lives when this app is served from Firebase Hosting (static files only).
// Served from Cloud Run itself, the app ignores this and calls its own origin.
window.BREEDERNEAR_API_BASE = "https://breedernear-655711985039.asia-south1.run.app";

// Firebase web config for "Continue with Google" (Firebase Authentication). These values are public by
// design: they identify the project to Firebase, and the key is restricted to this app's domains and to the
// sign-in APIs only. googleEnabled turns the button on once Google is enabled as a sign-in provider.
window.BREEDERNEAR_FIREBASE = { ...{"apiKey": "AIzaSyAWNJvmvf_f-I6J_VIAoZ8oVuEO33k1Mis", "authDomain": "breedernear-ai-2026.firebaseapp.com", "projectId": "breedernear-ai-2026", "appId": "1:655711985039:web:5da4dd18ed84b73584fffa"}, googleEnabled: false };
