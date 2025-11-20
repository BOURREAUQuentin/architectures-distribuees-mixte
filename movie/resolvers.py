import json
from graphql import GraphQLError
import requests, time
import config

# cache local pour stocker si un user est admin
# format : { "user_id": {"is_admin": True/False, "timestamp": 123456789} }
user_admin_cache = {}

# fonction utilitaire pour vérifier admin
def verify_admin(user_id):
    """
    Check if a user is an admin, with caching.

    Args:
        user_id (str): ID of the user to check.

    Returns:
        tuple: (is_admin (bool), error_response (Response or None))
               is_admin indicates if the user has admin privileges.
               error_response is a Flask response object if verification fails.
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
        raise GraphQLError("User service unsearchable")


with open('{}/databases/movies.json'.format("."), "r") as jsf:
    movies = json.load(jsf)["movies"]
    
def write(movies_data):
    with open('{}/databases/movies.json'.format("."), 'w') as f:
        full = {}
        full['movies'] = movies_data
        json.dump(full, f)

def movies_json(_,info, user_id):
    _, error = verify_admin(user_id)
    if error:
        return error
    
    return movies

def movie_with_id(_, info, user_id, id):
    _, error = verify_admin(user_id)
    if error:
        return error
    
    for movie in movies:
        if movie["id"] == id:
            return movie
    raise GraphQLError("Movie not found with id: " + id)


def movie_with_title(_,info, user_id, title):
    _, error = verify_admin(user_id)
    if error:
        return error
    
    for movie in movies:
        if str(movie["title"]) == title:
            return movie
    raise GraphQLError("Movie not found with title : " + title)

def add_movie(_, info, user_id,  id, title, rating, director):
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")
    
    for movie in movies:
        if str(movie["id"]) == id:
            raise GraphQLError("Movie ID already exists : " + id)
    newmovie = {
        "id": id,
        "title" : title,
        "rating" : rating,
        "director" : director
    }
    movies.append(newmovie)
    write(movies)
    return newmovie

def update_movie_rate(_,info, user_id, id,rating):
    _, error = verify_admin(user_id)
    if error:
        return error
    
    newmovie = None
    for movie in movies:
        if movie['id'] == id:
            movie['rating'] = rating
            newmovie = movie
        
    if newmovie is None:
        raise GraphQLError("Movie not found with id: " + id)
    
    write(movies)
    return newmovie

def remove_movie_with_id(_, info, user_id,  id):
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")
    
    removed_movie = None
        
    for movie in movies:
        if str(movie["id"]) == id:
            movies.remove(movie)
            removed_movie = movie
        
    if removed_movie is None:
        raise GraphQLError("Movie not found with id: " + id)

    write(movies)
    return movie