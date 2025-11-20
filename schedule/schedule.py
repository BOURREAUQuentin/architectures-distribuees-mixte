import grpc
from concurrent import futures
import schedule_pb2
import schedule_pb2_grpc
import requests
import time
import config
from pymongo import MongoClient

# Connexion MongoDB
client = MongoClient(config.MONGO_URI)
db = client[config.MONGO_DB_NAME]
schedules_collection = db['schedules']

# Cache pour vérification admin
user_admin_cache = {}


def verify_admin(user_id):
    """
    Vérifie si un utilisateur est admin avec mise en cache.

    Args:
        user_id (str): ID de l'utilisateur à vérifier

    Returns:
        tuple: (is_admin (bool), error (str or None))
    """
    now = time.time()

    if user_id in user_admin_cache:
        cached = user_admin_cache[user_id]
        if now - cached["timestamp"] < config.CACHE_TTL:
            return cached["is_admin"], None

    try:
        response = requests.get(f"{config.USER_BASE_URL}/users/{user_id}/is_admin")
        response.raise_for_status()
        data = response.json()
        is_admin = data.get("is_admin", False)
        user_admin_cache[user_id] = {"is_admin": is_admin, "timestamp": now}
        return is_admin, None

    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Unable to verify user ({response.status_code}): {e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"User service unreachable: {e}")


def serialize_schedule(schedule):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if schedule and '_id' in schedule:
        schedule['_id'] = str(schedule['_id'])
    return schedule


def fetch_movie_data(user_id, movie_id, context):
    """
    Récupère un film depuis le microservice GraphQL.

    Args:
        user_id (str): ID de l'utilisateur faisant la requête
        movie_id (str): ID du film à récupérer
        context: Contexte gRPC

    Returns:
        schedule_pb2.MovieData: Données du film
    """
    query = f"""
    {{
        movie_with_id(user_id: "{user_id}", id: "{movie_id}") {{
            id
            title
            director
            rating
        }}
    }}
    """
    try:
        response = requests.post(f"{config.MOVIE_BASE_URL}/graphql", json={"query": query})
        response.raise_for_status()
        data = response.json()
        movie_details = data.get("data", {}).get("movie_with_id")

        if not movie_details:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Movie not found for id {movie_id}")

        return schedule_pb2.MovieData(
            id=movie_details["id"],
            title=movie_details["title"],
            director=movie_details["director"],
            rating=movie_details["rating"]
        )

    except requests.exceptions.RequestException as e:
        context.abort(grpc.StatusCode.UNAVAILABLE, f"Movie service unreachable: {e}")


class ScheduleServicer(schedule_pb2_grpc.ScheduleServicer):

    def __init__(self):
        # Plus besoin de charger depuis un fichier JSON
        pass

    def _check_admin(self, user_id, context, require_admin=False):
        """
        Vérifie les permissions admin de l'utilisateur.

        Args:
            user_id (str): ID de l'utilisateur
            context: Contexte gRPC
            require_admin (bool): Si True, l'utilisateur doit être admin

        Returns:
            bool: True si l'utilisateur est admin
        """
        try:
            is_admin, _ = verify_admin(user_id)
        except Exception as e:
            context.abort(grpc.StatusCode.UNAVAILABLE, str(e))
        if require_admin and not is_admin:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Admin access required")
        return is_admin

    def GetJson(self, request, context):
        """
        Récupère tous les horaires avec les détails des films.

        Args:
            request: Requête contenant userId
            context: Contexte gRPC

        Yields:
            schedule_pb2.ScheduleData: Données d'horaire avec films
        """
        self._check_admin(request.userId, context)

        schedules = list(schedules_collection.find({}))

        for schedule in schedules:
            movies = [
                fetch_movie_data(request.userId, movie_id, context)
                for movie_id in schedule["movies"]
            ]
            yield schedule_pb2.ScheduleData(date=schedule["date"], movies=movies)

    def GetMoviesByDate(self, request, context):
        """
        Récupère les films programmés pour une date donnée.

        Args:
            request: Requête contenant userId et date
            context: Contexte gRPC

        Returns:
            schedule_pb2.ScheduleData: Données d'horaire pour la date
        """
        self._check_admin(request.userId, context)

        schedule = schedules_collection.find_one({"date": str(request.date)})

        if schedule:
            movies = [
                fetch_movie_data(request.userId, movie_id, context)
                for movie_id in schedule["movies"]
            ]
            return schedule_pb2.ScheduleData(date=schedule["date"], movies=movies)

        context.abort(grpc.StatusCode.NOT_FOUND, "No movies found for this date")

    def GetScheduleByMovie(self, request, context):
        """
        Récupère toutes les dates où un film est programmé.

        Args:
            request: Requête contenant userId et movieId
            context: Contexte gRPC

        Returns:
            schedule_pb2.DateData: Liste des dates
        """
        self._check_admin(request.userId, context)

        movie_id = request.movieId
        if not movie_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "movieId not provided")

        # Recherche toutes les dates contenant ce film
        schedules = list(schedules_collection.find({"movies": movie_id}))
        dates = [schedule["date"] for schedule in schedules]

        if not dates:
            context.abort(grpc.StatusCode.NOT_FOUND, "No dates found for this movie")

        return schedule_pb2.DateData(dates=dates)

    def AddSchedule(self, request, context):
        """
        Ajoute un nouvel horaire pour une date.

        Args:
            request: Requête contenant userId, date et moviesId
            context: Contexte gRPC

        Returns:
            schedule_pb2.ScheduleData: Nouvel horaire créé
        """
        self._check_admin(request.userId, context, require_admin=True)

        # Vérifier si la date existe déjà
        existing_schedule = schedules_collection.find_one({"date": str(request.date)})
        if existing_schedule:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "Schedule date already exists")

        # Valider l'existence des films
        movies = [
            fetch_movie_data(request.userId, movie_id, context)
            for movie_id in request.moviesId
        ]

        # Créer le nouvel horaire
        new_entry = {
            "date": request.date,
            "movies": [movie.id for movie in movies]
        }

        schedules_collection.insert_one(new_entry)

        return schedule_pb2.ScheduleData(date=request.date, movies=movies)

    def AddMovieToDate(self, request, context):
        """
        Ajoute un ou plusieurs films à une date existante ou crée la date.

        Args:
            request: Requête contenant userId, date et moviesId
            context: Contexte gRPC

        Returns:
            schedule_pb2.ScheduleData: Horaire mis à jour
        """
        self._check_admin(request.userId, context, require_admin=True)

        if not request.moviesId:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "At least one movieId required")

        target_date = str(request.date)

        # Rechercher si la date existe
        existing_date = schedules_collection.find_one({"date": target_date})

        if existing_date:
            # Vérifier les doublons
            already_scheduled = [
                mid for mid in request.moviesId if mid in existing_date["movies"]
            ]
            if already_scheduled:
                context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Movies already scheduled for this date: {already_scheduled}"
                )

            # Ajouter les nouveaux films
            schedules_collection.update_one(
                {"date": target_date},
                {"$push": {"movies": {"$each": list(request.moviesId)}}}
            )

            # Récupérer l'horaire mis à jour
            updated_schedule = schedules_collection.find_one({"date": target_date})
            added_movies = [
                fetch_movie_data(request.userId, mid, context)
                for mid in updated_schedule["movies"]
            ]
            return schedule_pb2.ScheduleData(date=target_date, movies=added_movies)

        # Créer une nouvelle entrée si la date n'existe pas
        new_entry = {
            "date": target_date,
            "movies": list(request.moviesId)
        }
        schedules_collection.insert_one(new_entry)

        added_movies = [
            fetch_movie_data(request.userId, mid, context)
            for mid in request.moviesId
        ]
        return schedule_pb2.ScheduleData(date=target_date, movies=added_movies)

    def DeleteDate(self, request, context):
        """
        Supprime un horaire complet pour une date donnée.

        Args:
            request: Requête contenant userId et date
            context: Contexte gRPC

        Returns:
            schedule_pb2.Empty: Réponse vide
        """
        self._check_admin(request.userId, context, require_admin=True)

        target_date = str(request.date)

        result = schedules_collection.delete_one({"date": target_date})

        if result.deleted_count == 0:
            context.abort(grpc.StatusCode.NOT_FOUND, "Date not found")

        return schedule_pb2.Empty()

    def DeleteMovieFromDate(self, request, context):
        """
        Supprime un ou plusieurs films d'une date donnée.

        Args:
            request: Requête contenant userId, date et moviesId
            context: Contexte gRPC

        Returns:
            schedule_pb2.Empty: Réponse vide
        """
        self._check_admin(request.userId, context, require_admin=True)

        if not request.moviesId:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "moviesId list required")

        target_date = str(request.date)
        movies_to_remove = list(request.moviesId)

        # Vérifier si la date existe
        schedule = schedules_collection.find_one({"date": target_date})

        if not schedule:
            context.abort(grpc.StatusCode.NOT_FOUND, "Date not found")

        # Vérifier si les films existent dans cet horaire
        existing_movies = set(schedule["movies"])
        found_movies = set(movies_to_remove) & existing_movies

        if not found_movies:
            context.abort(grpc.StatusCode.NOT_FOUND, "None of the movies found in this date")

        # Supprimer les films
        schedules_collection.update_one(
            {"date": target_date},
            {"$pull": {"movies": {"$in": movies_to_remove}}}
        )

        return schedule_pb2.Empty()


def serve():
    """Démarre le serveur gRPC."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    schedule_pb2_grpc.add_ScheduleServicer_to_server(ScheduleServicer(), server)
    server.add_insecure_port(f"[::]:{config.SCHEDULE_PORT}")
    print(f"Schedule service started on port {config.SCHEDULE_PORT}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()