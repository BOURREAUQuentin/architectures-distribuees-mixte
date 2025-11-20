from graphql import GraphQLError
import requests
import time
import grpc
import config
from pymongo import MongoClient
from schedule_client import get_schedule_client
import schedule_pb2

# Connexion MongoDB
client = MongoClient(config.MONGO_URI)
db = client[config.MONGO_DB_NAME]
bookings_collection = db['bookings']

# cache local pour stocker si un user est admin
user_admin_cache = {}  # format: { user_id: { "is_admin": bool, "timestamp": float } }

# Client gRPC Schedule
schedule = get_schedule_client()


def serialize_booking(booking):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if booking and '_id' in booking:
        booking['_id'] = str(booking['_id'])
    return booking


def verify_admin(user_id):
    """
    Vérifie si user_id est admin, avec cache.
    
    Args:
        user_id (str): ID de l'utilisateur à vérifier
        
    Returns:
        tuple: (is_admin (bool), error (GraphQLError or None))
    
    Raises:
        GraphQLError: Si le service User est injoignable ou répond avec une erreur
    """
    now = time.time()
    if user_id in user_admin_cache:
        cached = user_admin_cache[user_id]
        if now - cached["timestamp"] < config.CACHE_TTL:
            return cached["is_admin"], None

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


def resolve_booking_userid(booking, info):
    """
    Résout le champ 'user' d'un booking en récupérant les détails de l'utilisateur.
    
    Args:
        booking (dict): Réservation contenant userid
        info: Contexte GraphQL
        
    Returns:
        dict: Détails de l'utilisateur
        
    Raises:
        GraphQLError: Si l'utilisateur n'est pas trouvé ou service injoignable
    """
    user_id = booking["userid"]

    try:
        # Appel au service User pour récupérer les détails (en simulant admin pour avoir les droits)
        r = requests.get(f"{config.USER_BASE_URL}/chris_rivers/users/{user_id}")
        if r.status_code == 200:
            return r.json()
        raise GraphQLError(f"User not found: {user_id}")
    except requests.exceptions.RequestException:
        raise GraphQLError("User service unreachable")


def resolve_booking_dates(booking, info):
    """
    Résout le champ 'dates' d'un booking en ajoutant le userid à chaque date.
    
    Args:
        booking (dict): Réservation contenant les dates
        info: Contexte GraphQL
        
    Returns:
        list: Liste des dates avec userid ajouté
    """
    dates_to_return = []
    for date in booking["dates"]:
        date["user_id"] = booking["userid"]
        dates_to_return.append(date)
    return dates_to_return


def resolve_date_movies(date, info):
    """
    Résout le champ 'movies' d'une date en récupérant les détails des films.
    
    Args:
        date (dict): Date contenant la liste des movie IDs
        info: Contexte GraphQL
        
    Returns:
        list: Liste des détails des films
        
    Raises:
        GraphQLError: Si un film n'est pas trouvé ou service injoignable
    """
    user_id = date["user_id"]
    movies_to_return = []

    for movieid in date["movies"]:
        query = f"""
        {{
            movie_with_id(user_id: "{user_id}", id: "{movieid}") {{
                id
                title
                director
                rating
            }}
        }}
        """
        try:
            response = requests.post(f"{config.MOVIE_BASE_URL}/graphql", json={'query': query})
            response.raise_for_status()
            data = response.json()

            if "data" in data and "movie_with_id" in data["data"]:
                movie_details = data["data"]["movie_with_id"]
                movies_to_return.append(movie_details)
            else:
                raise GraphQLError(f"Invalid movie service response for id {movieid}: {data}")
        except (requests.exceptions.RequestException, ValueError) as e:
            raise GraphQLError(f"Movie service unreachable or invalid JSON: {e}")

    return movies_to_return


def bookings_json(_, info, user_id):
    """
    Récupère toutes les réservations.
    
    Args:
        user_id (str): ID de l'utilisateur faisant la requête
        
    Returns:
        list: Liste de toutes les réservations
        
    Raises:
        GraphQLError: Si la vérification de l'utilisateur échoue
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    bookings = list(bookings_collection.find({}))
    return [serialize_booking(booking) for booking in bookings]


def booking_with_id(_, info, user_id, id):
    """
    Récupère une réservation par l'ID utilisateur.
    
    Args:
        user_id (str): ID de l'utilisateur faisant la requête
        id (str): ID de l'utilisateur dont on veut la réservation
        
    Returns:
        dict: Réservation de l'utilisateur
        
    Raises:
        GraphQLError: Si la réservation n'est pas trouvée
    """
    _, error = verify_admin(user_id)
    if error:
        raise error

    booking = bookings_collection.find_one({"userid": id})

    if booking:
        return serialize_booking(booking)

    raise GraphQLError(f"Booking not found with id: {id}")


def add_booking(_, info, user_id, userid, date, movieid):
    """
    Ajoute une réservation pour un utilisateur à une date donnée.
    
    Args:
        user_id (str): ID de l'utilisateur faisant la requête (doit être admin)
        userid (str): ID de l'utilisateur pour qui créer la réservation
        date (str): Date de la réservation
        movieid (str): ID du film à réserver
        
    Returns:
        dict: Réservation mise à jour ou créée
        
    Raises:
        GraphQLError: Si l'utilisateur n'est pas admin, le film n'est pas programmé,
                     ou la réservation existe déjà
    """
    is_admin, error = verify_admin(user_id)
    if error:
        raise error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    # Vérifie auprès de Schedule que le film est dispo à cette date
    try:
        response = schedule.GetMoviesByDate(
            schedule_pb2.GetMoviesByDateRequest(
                userId=user_id,
                date=str(date)
            )
        )
        movie_ids = [m.id for m in response.movies]
        if movieid not in movie_ids:
            raise GraphQLError("Movie not scheduled on this date")

    except grpc.RpcError as e:
        raise GraphQLError(f"Schedule service error: {e.details()}")

    # Chercher si l'utilisateur a déjà des réservations
    existing_booking = bookings_collection.find_one({"userid": userid})

    if existing_booking:
        # Vérifier si la date existe déjà
        date_found = False
        for d in existing_booking["dates"]:
            if d["date"] == date:
                date_found = True
                # Vérifier si le film est déjà réservé
                if movieid in d["movies"]:
                    raise GraphQLError("Booking already exists")

                # Ajouter le film à la date existante
                bookings_collection.update_one(
                    {"userid": userid, "dates.date": date},
                    {"$push": {"dates.$.movies": movieid}}
                )
                break

        # Si la date n'existe pas, l'ajouter
        if not date_found:
            bookings_collection.update_one(
                {"userid": userid},
                {"$push": {"dates": {"date": date, "movies": [movieid]}}}
            )

        # Retourner la réservation mise à jour
        updated_booking = bookings_collection.find_one({"userid": userid})
        return serialize_booking(updated_booking)

    # Si l'utilisateur n'a pas encore de réservations, créer une nouvelle entrée
    newbooking = {
        "userid": userid,
        "dates": [
            {
                "date": date,
                "movies": [movieid]
            }
        ]
    }

    bookings_collection.insert_one(newbooking)
    return serialize_booking(newbooking)


def remove_booking_with_movie_date_user(_, info, user_id, userid, date, movieid):
    """
    Supprime un film spécifique d'une réservation.
    
    Args:
        user_id (str): ID de l'utilisateur faisant la requête (doit être admin)
        userid (str): ID de l'utilisateur dont on veut modifier la réservation
        date (str): Date de la réservation
        movieid (str): ID du film à supprimer
        
    Returns:
        dict: Réservation mise à jour
        
    Raises:
        GraphQLError: Si l'utilisateur n'est pas admin, la réservation n'existe pas,
                     ou le film n'est pas trouvé
    """
    is_admin, error = verify_admin(user_id)
    if error:
        raise error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    # Vérifier que la réservation existe
    booking = bookings_collection.find_one({"userid": userid})

    if not booking:
        raise GraphQLError("Booking not found")

    # Vérifier que la date et le film existent
    date_found = False
    movie_found = False

    for d in booking["dates"]:
        if d["date"] == date:
            date_found = True
            if movieid in d["movies"]:
                movie_found = True
                break

    if not date_found:
        raise GraphQLError("Booking not found")

    if not movie_found:
        raise GraphQLError("Movie not found in this booking")

    # Supprimer le film de la date
    bookings_collection.update_one(
        {"userid": userid, "dates.date": date},
        {"$pull": {"dates.$.movies": movieid}}
    )

    # Retourner la réservation mise à jour
    updated_booking = bookings_collection.find_one({"userid": userid})
    return serialize_booking(updated_booking)


def remove_bookings_with_user_id(_, info, user_id, userid):
    """
    Supprime toutes les réservations d'un utilisateur.
    
    Args:
        user_id (str): ID de l'utilisateur faisant la requête (doit être admin)
        userid (str): ID de l'utilisateur dont on veut supprimer les réservations
        
    Returns:
        str: Message de confirmation
        
    Raises:
        GraphQLError: Si l'utilisateur n'est pas admin ou l'utilisateur n'est pas trouvé
    """
    is_admin, error = verify_admin(user_id)
    if error:
        raise error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    result = bookings_collection.delete_one({"userid": userid})

    if result.deleted_count == 0:
        raise GraphQLError("User not found")

    return f"All bookings removed for userid: {userid}"