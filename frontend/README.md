# Movie Recommender App

A movie recommendation web app built with **Streamlit** (frontend) and **Flask** (backend).

The app allows users to:
- search movies
- select favorite movies
- get personalized recommendations
- view movie posters

The project uses:
- **BigQuery** for movie and rating data
- **Elasticsearch** for search
- **TMDB API** for posters
- **Google Cloud Run** for deployment

## Live URLs

**Frontend**  
https://movie-frontend-879168890374.europe-west1.run.app

**Backend**  
https://movie-backend-879168890374.europe-west1.run.app

## Recommendation method

The app uses a cold-start recommendation strategy:
- the user selects movies they like
- the backend finds similar users who liked the same movies
- it recommends other movies liked by those similar users
- already selected movies are excluded

If no movie is selected, the app returns popular movies.

## Architecture

- **Frontend:** Streamlit
- **Backend:** Flask + Gunicorn
- **Search:** Elasticsearch
- **Data:** BigQuery
- **Posters:** TMDB API

## Project structure

```text
Cloud-Assignment2/
├── README.md
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── app.py
    ├── requirements.txt
    └── Dockerfile
Notes
    •    The backend root URL may return Not Found because / is not defined.
    •    The frontend is the main application URL.
    •    Search is powered by Elasticsearch.

Final result

Frontend
https://movie-frontend-879168890374.europe-west1.run.app

Backend
https://movie-backend-879168890374.europe-west1.run.app
