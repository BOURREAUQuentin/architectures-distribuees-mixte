import grpc
from concurrent import futures
import schedule_pb2
import schedule_pb2_grpc
import json
import requests
import time

movie_url = "http://movie:3200"
user_url = "http://user:3201"

cache_ttl = 60
user_admin_cache = {}


def verify_admin(user_id):
    now = time.time()

    if user_id in user_admin_cache:
        cached = user_admin_cache[user_id]
        if now - cached["timestamp"] < cache_ttl:
            return cached["is_admin"], None

    try:
        response = requests.get(f"{user_url}/users/{user_id}/is_admin")
        response.raise_for_status()
        data = response.json()
        is_admin = data.get("is_admin", False)
        user_admin_cache[user_id] = {"is_admin": is_admin, "timestamp": now}
        return is_admin, None

    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Unable to verify user ({response.status_code}): {e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"User service unreachable: {e}")


def write(schedule_data):
    with open("./databases/times.json", "w") as file:
        json.dump({"schedule": schedule_data}, file)


def fetch_movie_data(user_id, movie_id, context):
    """Récupère un film depuis le microservice GraphQL"""
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
        response = requests.post(f"{movie_url}/graphql", json={"query": query})
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
        with open("./databases/times.json", "r") as js_file:
            self.db = json.load(js_file)["schedule"]

    def _check_admin(self, user_id, context, require_admin=False):
        try:
            is_admin, _ = verify_admin(user_id)
        except Exception as e:
            context.abort(grpc.StatusCode.UNAVAILABLE, str(e))
        if require_admin and not is_admin:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Admin access required")
        return is_admin

    def GetJson(self, request, context):
        self._check_admin(request.userId, context)
        for schedule in self.db:
            movies = [
                fetch_movie_data(request.userId, movie_id, context)
                for movie_id in schedule["movies"]
            ]
            yield schedule_pb2.ScheduleData(date=schedule["date"], movies=movies)

    def GetMoviesByDate(self, request, context):
        self._check_admin(request.userId, context)
        for schedule in self.db:
            if str(schedule["date"]) == str(request.date):
                movies = [
                    fetch_movie_data(request.userId, movie_id, context)
                    for movie_id in schedule["movies"]
                ]
                return schedule_pb2.ScheduleData(date=schedule["date"], movies=movies)
        context.abort(grpc.StatusCode.NOT_FOUND, "No movies found for this date")

    def GetScheduleByMovie(self, request, context):
        self._check_admin(request.userId, context)
        movie_id = request.movieId
        if not movie_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "movieId not provided")
        dates = [schedule["date"] for schedule in self.db if movie_id in schedule["movies"]]
        if not dates:
            context.abort(grpc.StatusCode.NOT_FOUND, "No dates found for this movie")
        return schedule_pb2.DateData(dates=dates)

    def AddSchedule(self, request, context):
        self._check_admin(request.userId, context, require_admin=True)
        for schedule in self.db:
            if str(schedule["date"]) == str(request.date):
                context.abort(grpc.StatusCode.ALREADY_EXISTS, "Schedule date already exists")

        movies = [
            fetch_movie_data(request.userId, movie_id, context)
            for movie_id in request.moviesId
        ]
        new_entry = {"date": request.date, "movies": [movie.id for movie in movies]}
        self.db.append(new_entry)
        write(self.db)
        return schedule_pb2.ScheduleData(date=request.date, movies=movies)

    def AddMovieToDate(self, request, context):
        self._check_admin(request.userId, context, require_admin=True)

        if not request.moviesId:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "At least one movieId required")

        target_date = str(request.date)
        added_movies = []
        existing_date = None

        for schedule in self.db:
            if str(schedule["date"]) == target_date:
                existing_date = schedule
                break

        if existing_date:
            already_scheduled = [
                mid for mid in request.moviesId if mid in existing_date["movies"]
            ]
            if already_scheduled:
                context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Movies already scheduled for this date: {already_scheduled}"
                )

            existing_date["movies"].extend(request.moviesId)
            write(self.db)

            added_movies = [
                fetch_movie_data(request.userId, mid, context)
                for mid in existing_date["movies"]
            ]
            return schedule_pb2.ScheduleData(date=target_date, movies=added_movies)

        new_entry = {"date": target_date, "movies": list(request.moviesId)}
        self.db.append(new_entry)
        write(self.db)

        added_movies = [
            fetch_movie_data(request.userId, mid, context)
            for mid in request.moviesId
        ]
        return schedule_pb2.ScheduleData(date=target_date, movies=added_movies)


    def DeleteDate(self, request, context):
        self._check_admin(request.userId, context, require_admin=True)
        target_date = str(request.date)

        new_schedule = [s for s in self.db if str(s["date"]) != target_date]
        if len(new_schedule) == len(self.db):
            context.abort(grpc.StatusCode.NOT_FOUND, "Date not found")

        self.db = new_schedule
        write(self.db)
        return schedule_pb2.Empty()

    def DeleteMovieFromDate(self, request, context):
        self._check_admin(request.userId, context, require_admin=True)

        if not request.moviesId:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "moviesId list required")

        target_date = str(request.date)
        movies_to_remove = set(request.moviesId)

        for schedule in self.db:
            if str(schedule["date"]) == target_date:
                existing_movies = set(schedule["movies"])
                found_movies = movies_to_remove & existing_movies

                if not found_movies:
                    context.abort(grpc.StatusCode.NOT_FOUND, "None of the movies found in this date")

                schedule["movies"] = list(existing_movies - found_movies)
                write(self.db)
                return schedule_pb2.Empty()

        context.abort(grpc.StatusCode.NOT_FOUND, "Date not found" + request.date)



def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    schedule_pb2_grpc.add_ScheduleServicer_to_server(ScheduleServicer(), server)
    server.add_insecure_port("[::]:3202")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
