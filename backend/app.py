from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import bigquery
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import os
import requests

app = Flask(__name__)
CORS(app)

client = bigquery.Client(project="cloud-analytics-489523")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

es = Elasticsearch(
    ELASTICSEARCH_URL,
    api_key=ELASTIC_API_KEY,
)


def get_poster_url(tmdb_id):
    if not tmdb_id or not TMDB_API_KEY:
        return None

    full_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"

    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        poster_path = data.get("poster_path")
        if not poster_path:
            return None

        return f"{TMDB_IMAGE_BASE}{poster_path}"
    except Exception:
        return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "tmdb_key_loaded": bool(TMDB_API_KEY)
    })


@app.route("/popular", methods=["GET"])
def popular():
    query = """
    SELECT
      r.movieId,
      m.title,
      l.tmdbId,
      COUNT(*) AS liked_by_users,
      AVG(r.rating_im) AS avg_rating_im
    FROM `cloud-analytics-489523.assignment2_movies.ratings` AS r
    JOIN `cloud-analytics-489523.assignment2_movies.movies` AS m
      ON r.movieId = m.movieId
    LEFT JOIN `cloud-analytics-489523.assignment2_movies.links` AS l
      ON r.movieId = l.movieId
    WHERE r.rating_im >= 0.5
    GROUP BY r.movieId, m.title, l.tmdbId
    ORDER BY liked_by_users DESC, avg_rating_im DESC
    LIMIT 20
    """

    rows = client.query(query).result()

    results = []
    for row in rows:
        results.append({
            "movieId": row.movieId,
            "title": row.title,
            "tmdbId": row.tmdbId,
            "poster_url": get_poster_url(row.tmdbId),
            "liked_by_users": row.liked_by_users,
            "avg_rating_im": row.avg_rating_im,
        })

    return jsonify(results)


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True) or {}
    movie_ids = data.get("movie_ids", [])

    if not movie_ids:
        return popular()

    selected_movies_sql = "\nUNION ALL\n".join(
        [
            f"SELECT {int(movie_id)} AS movieId" if i == 0 else f"SELECT {int(movie_id)}"
            for i, movie_id in enumerate(movie_ids)
        ]
    )

    query = f"""
    WITH selected_movies AS (
      {selected_movies_sql}
    ),
    similar_users AS (
      SELECT
        r.userId,
        COUNT(*) AS common_liked_movies
      FROM `cloud-analytics-489523.assignment2_movies.ratings` AS r
      JOIN selected_movies sm
        ON r.movieId = sm.movieId
      WHERE r.rating_im >= 0.5
      GROUP BY r.userId
      ORDER BY common_liked_movies DESC, r.userId
      LIMIT 10
    ),
    candidate_movies AS (
      SELECT
        r.movieId,
        COUNT(DISTINCT r.userId) AS liked_by_similar_users,
        AVG(r.rating_im) AS avg_rating_im
      FROM `cloud-analytics-489523.assignment2_movies.ratings` AS r
      JOIN similar_users su
        ON r.userId = su.userId
      WHERE r.rating_im >= 0.5
        AND r.movieId NOT IN (SELECT movieId FROM selected_movies)
      GROUP BY r.movieId
    )
    SELECT
      cm.movieId,
      m.title,
      l.tmdbId,
      cm.liked_by_similar_users,
      cm.avg_rating_im
    FROM candidate_movies cm
    JOIN `cloud-analytics-489523.assignment2_movies.movies` AS m
      ON cm.movieId = m.movieId
    LEFT JOIN `cloud-analytics-489523.assignment2_movies.links` AS l
      ON cm.movieId = l.movieId
    ORDER BY
      cm.liked_by_similar_users DESC,
      cm.avg_rating_im DESC
    LIMIT 20
    """

    rows = client.query(query).result()

    results = []
    for row in rows:
        results.append({
            "movieId": row.movieId,
            "title": row.title,
            "tmdbId": row.tmdbId,
            "poster_url": get_poster_url(row.tmdbId),
            "liked_by_similar_users": row.liked_by_similar_users,
            "avg_rating_im": row.avg_rating_im,
        })

    return jsonify(results)


@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    try:
        response = es.search(
            index="movies",
            query={
                "multi_match": {
                    "query": q,
                    "fields": ["title^2", "title.keyword"],
                    "type": "best_fields"
                }
            },
            size=20
        )

        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            source = hit["_source"]
            movie_id = source["movieId"]

            tmdb_query = """
            SELECT tmdbId
            FROM `cloud-analytics-489523.assignment2_movies.links`
            WHERE movieId = @movie_id
            LIMIT 1
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("movie_id", "INT64", movie_id)
                ]
            )

            tmdb_rows = list(client.query(tmdb_query, job_config=job_config).result())
            tmdb_id = tmdb_rows[0].tmdbId if tmdb_rows else None

            results.append({
                "movieId": movie_id,
                "title": source["title"],
                "tmdbId": tmdb_id,
                "poster_url": get_poster_url(tmdb_id),
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/es-health", methods=["GET"])
def es_health():
    try:
        info = es.info()
        return jsonify({
            "ok": True,
            "cluster_name": info.get("cluster_name"),
            "version": info.get("version", {}).get("number"),
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500


@app.route("/all-movies", methods=["GET"])
def all_movies():
    query = """
    SELECT
      m.movieId,
      m.title,
      l.tmdbId
    FROM `cloud-analytics-489523.assignment2_movies.movies` AS m
    LEFT JOIN `cloud-analytics-489523.assignment2_movies.links` AS l
      ON m.movieId = l.movieId
    ORDER BY m.title
    """

    rows = client.query(query).result()

    results = []
    for row in rows:
        results.append({
            "movieId": row.movieId,
            "title": row.title,
            "tmdbId": row.tmdbId,
            "poster_url": get_poster_url(row.tmdbId),
        })

    return jsonify(results)


@app.route("/index-movies", methods=["POST"])
def index_movies():
    try:
        if es.indices.exists(index="movies"):
            es.indices.delete(index="movies")

        es.indices.create(
            index="movies",
            mappings={
                "properties": {
                    "movieId": {"type": "integer"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    }
                }
            }
        )

        query = """
        SELECT movieId, title
        FROM `cloud-analytics-489523.assignment2_movies.movies`
        """

        rows = client.query(query).result()

        actions = []
        count = 0

        for row in rows:
            actions.append({
                "_index": "movies",
                "_id": row.movieId,
                "_source": {
                    "movieId": row.movieId,
                    "title": row.title,
                }
            })
            count += 1

        bulk(es, actions, chunk_size=500, request_timeout=300)
        es.indices.refresh(index="movies")

        return jsonify({
            "ok": True,
            "indexed_movies": count
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)
