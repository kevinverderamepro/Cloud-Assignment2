import os
import streamlit as st
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(page_title="Movie Recommender", layout="wide")
st.title("Movie Recommender")
st.write("Search movies with Elasticsearch, add several favorites, and get recommendations.")

if "selected_movies" not in st.session_state:
    st.session_state.selected_movies = []

search_query = st.text_input("Search a movie title", value="")

search_results = []
if search_query.strip():
    try:
        response = requests.get(
            f"{BACKEND_URL}/search",
            params={"q": search_query},
            timeout=120,
        )
        response.raise_for_status()
        search_results = response.json()
    except Exception as e:
        st.error(f"Search error: {e}")

options = {}
for movie in search_results:
    label = movie["title"]
    if label in options:
        label = f"{movie['title']} (id={movie['movieId']})"
    options[label] = movie

selected_labels = st.multiselect(
    "Suggestions",
    options=list(options.keys()),
    placeholder="Choose one or more movies..."
)

selected_suggestion_movies = [options[label] for label in selected_labels]

if selected_suggestion_movies:
    st.subheader("Movies to add")
    cols = st.columns(4)

    for i, movie in enumerate(selected_suggestion_movies):
        with cols[i % 4]:
            if movie.get("poster_url"):
                st.image(movie["poster_url"], use_container_width=True)
            st.caption(movie["title"])

    if st.button("Add selected movies"):
        existing_ids = {movie["movieId"] for movie in st.session_state.selected_movies}

        for movie in selected_suggestion_movies:
            if movie["movieId"] not in existing_ids:
                st.session_state.selected_movies.append(movie)

        st.rerun()

if st.session_state.selected_movies:
    st.subheader("Selected movies")
    cols = st.columns(4)

    for i, movie in enumerate(st.session_state.selected_movies):
        with cols[i % 4]:
            if movie.get("poster_url"):
                st.image(movie["poster_url"], use_container_width=True)
            st.caption(movie["title"])
            if st.button("Remove", key=f"remove_{movie['movieId']}"):
                st.session_state.selected_movies = [
                    m for m in st.session_state.selected_movies
                    if m["movieId"] != movie["movieId"]
                ]
                st.rerun()

selected_movie_ids = [movie["movieId"] for movie in st.session_state.selected_movies]

if st.button("Get recommendations", disabled=len(selected_movie_ids) == 0):
    try:
        response = requests.post(
            f"{BACKEND_URL}/recommend",
            json={"movie_ids": selected_movie_ids},
            timeout=120,
        )
        response.raise_for_status()
        recommendations = response.json()

        if recommendations:
            st.subheader("Recommendations")
            cols = st.columns(4)

            for i, movie in enumerate(recommendations):
                with cols[i % 4]:
                    if movie.get("poster_url"):
                        st.image(movie["poster_url"], use_container_width=True)
                    st.caption(movie["title"])
        else:
            st.info("No recommendations found.")
    except Exception as e:
        st.error(f"Recommendation error: {e}")
