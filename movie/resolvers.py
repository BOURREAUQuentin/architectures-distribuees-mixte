from graphql import GraphQLError
import requests
import time
import config
from pymongo import MongoClient

# Connexion MongoDB
client = MongoClient(config.MONGO_URI)
db = client[config.MONGO_DB_NAME]
movies_collection = db['movies']

# cache local pour stocker si un user est admin
# format : { "user_id": {"is_admin": True/False, "timestamp": 123456789} }
user_admin_cache = {}

# Helper pour convertir ObjectId en string dans les réponses
def serialize_movie(movie):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if movie and '_id' in movie:
        movie['_id'] = str(movie['_id'])
    return movie

# fonction utilitaire pour vérifier admin
def verify_admin(user_id):
    """
    Check if a user is an admin, with caching.

    Args:
        user_id (str): ID of the user to check.

    Returns:
        tuple: (is_admin (bool), error_response (GraphQLError or None))
               is_admin indicates if the user has admin privileges.
               error_response is a GraphQLError if verification fails.
    """
    now = time.time()

    # vérifie si on a une valeur en cache et qu'elle est encore valide
    if user_id in user_admin_cache:
        cached = user_admin_cache[user_id]
        if now - cached["timestamp"] < config.CACHE_TTL:
            return cached["is_admin"], None

    # sinon appelle le microservice User
    try:
        r = requests.get(f"{config.USER_BASE_URL}/users/{user_id}/is_admin")
        if r.status_code == 200:
            data = r.json()
            is_admin = data.get("is_admin", False)
            user_admin_cache[user_id] = {"is_admin": is_admin, "timestamp": now}
            return is_admin, None
        else:
            raise GraphQLError("Unable to verify user")
    except requests.exceptions.RequestException:
        raise GraphQLError("User service unreachable")

def movies_json(_, info, user_id):
    """
    Retrieve all movies in JSON format.

    Args:
        user_id (str): ID of the requesting user.

    Returns:
        list: List of all movies if requester is admin.
    
    Raises:
        GraphQLError: If user verification fails or user is not admin.
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    movies = list(movies_collection.find({}))
    return [serialize_movie(movie) for movie in movies]

def movie_with_id(_, info, user_id, id):
    """
    Retrieve a movie by its ID.

    Args:
        user_id (str): ID of the requesting user.
        id (str): ID of the movie to retrieve.

    Returns:
        dict: Movie details if found.
    
    Raises:
        GraphQLError: If movie not found or user verification fails.
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    movie = movies_collection.find_one({"id": id})

    if movie:
        return serialize_movie(movie)

    raise GraphQLError(f"Movie not found with id: {id}")

def movie_with_title(_, info, user_id, title):
    """
    Retrieve a movie by its title.

    Args:
        user_id (str): ID of the requesting user.
        title (str): Title of the movie to search for.

    Returns:
        dict: Movie details if found.
    
    Raises:
        GraphQLError: If movie not found or user verification fails.
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    movie = movies_collection.find_one({"title": title})

    if movie:
        return serialize_movie(movie)

    raise GraphQLError(f"Movie not found with title: {title}")

def add_movie(_, info, user_id, id, title, rating, director):
    """
    Add a new movie to the database.

    Args:
        user_id (str): ID of the requesting user.
        id (str): ID for the new movie.
        title (str): Title of the movie.
        rating (float): Rating of the movie.
        director (str): Director of the movie.

    Returns:
        dict: The newly added movie.
    
    Raises:
        GraphQLError: If user is not admin, movie ID already exists, or verification fails.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        raise error

    # si pas admin -> accès interdit
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    # Vérifier si le film existe déjà
    existing_movie = movies_collection.find_one({"id": id})
    if existing_movie:
        raise GraphQLError(f"Movie ID already exists: {id}")

    newmovie = {
        "id": id,
        "title": title,
        "rating": rating,
        "director": director
    }

    movies_collection.insert_one(newmovie)
    return serialize_movie(newmovie)

def update_movie_rate(_, info, user_id, id, rating):
    """
    Update the rating of an existing movie.

    Args:
        user_id (str): ID of the requesting user.
        id (str): ID of the movie to update.
        rating (float): New rating for the movie.

    Returns:
        dict: The updated movie.
    
    Raises:
        GraphQLError: If movie not found or user verification fails.
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    result = movies_collection.find_one_and_update(
        {"id": id},
        {"$set": {"rating": rating}},
        return_document=True
    )

    if result:
        return serialize_movie(result)

    raise GraphQLError(f"Movie not found with id: {id}")

def remove_movie_with_id(_, info, user_id, id):
    """
    Delete a movie by its ID.

    Args:
        user_id (str): ID of the requesting user.
        id (str): ID of the movie to delete.

    Returns:
        dict: The deleted movie.
    
    Raises:
        GraphQLError: If user is not admin, movie not found, or verification fails.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        raise error

    # si pas admin -> accès interdit
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    removed_movie = movies_collection.find_one_and_delete({"id": id})

    if removed_movie:
        return serialize_movie(removed_movie)

    raise GraphQLError(f"Movie not found with id: {id}")