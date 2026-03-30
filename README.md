# Cloud & Advanced Analytics 2026 - Assignment Part 2

Movie recommendation web application deployed on Google Cloud Run.

## URLs
Frontend: https://movie-frontend-879168890374.europe-west1.run.app  
Backend: https://movie-backend-879168890374.europe-west1.run.app

## Stack
- Streamlit frontend
- Flask backend
- BigQuery
- Elasticsearch
- TMDB API
- Docker
- Google Cloud Run

## Similarity method
For a cold-start user, the system finds similar users by looking at users who rated the same selected movies highly. Users are ranked by the number of common preferred movies, and recommendations are generated from the top similar users.

## Project structure
- backend/
- frontend/
