import json
from graphql import GraphQLError
import requests, time

SCHEDULE_URL = "http://schedule:3202" # service Schedule
MOVIE_URL   = "http://movie:3200" # service Movie
USER_URL  = "http://user:3201" # microservice User

# cache local pour stocker si un user est admin
CACHE_TTL = 60 # secondes de validité du cache pour is_admin
user_admin_cache = {}  # format: { user_id: { "is_admin": bool, "timestamp": float } }

def verify_admin(user_id):
    """
    Vérifie si user_id est admin, avec cache.
    Retourne (is_admin, None) ou lève GraphQLError en cas d'erreur de contact.
    """
    now = time.time()
    if user_id in user_admin_cache:
        cached = user_admin_cache[user_id]
        if now - cached["timestamp"] < CACHE_TTL:
            return cached["is_admin"], None

    try:
        r = requests.get(f"{USER_URL}/users/{user_id}/is_admin")
        if r.status_code == 200:
            data = r.json()
            is_admin = data.get("is_admin", False)
            user_admin_cache[user_id] = {"is_admin": is_admin, "timestamp": now}
            return is_admin, None
        else:
            raise GraphQLError("Unable to verify user")
    except requests.exceptions.RequestException:
        raise GraphQLError("User service unsearchable")

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
    bookings = json.load(jsf)["bookings"]
    
def write(bookings_data):
    with open('{}/databases/bookings.json'.format("."), 'w') as f:
        full = {}
        full['bookings'] = bookings_data
        json.dump(full, f)

def resolve_booking_userid(booking, info):
    user_id = booking["userid"]
    with open('../user/databases/users.json') as file:
        users = json.load(file)["users"]
    for user in users:
        if user["id"] == user_id:
            return user
    raise GraphQLError("User not found: " + user_id)

def resolve_booking_dates(booking, info):
    dates_to_return = []
    for date in booking["dates"]:
        date["user_id"] = booking["userid"]
        dates_to_return.append(date)
    return dates_to_return

def resolve_date_movies(date, info):
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
            response = requests.post(f"{MOVIE_URL}/graphql", json={'query': query})
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


# Lecture -> on exige que le service User soit joignable (verify_admin appelé), mais on n'impose pas le role admin
def bookings_json(_, info, user_id):
    _, error = verify_admin(user_id)
    if error:
        return error
    return bookings

# Lecture par id -> idem
def booking_with_id(_, info, user_id, id):
    _, error = verify_admin(user_id)
    if error:
        return error
    for booking in bookings:
        if booking["userid"] == id:
            return booking
    raise GraphQLError("Booking not found with id: " + id)

# Mutations nécessitent un admin
def add_booking(_, info, user_id, userid, date, movieid):
    is_admin, error = verify_admin(user_id)
    if error:
        return error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    # vérifie auprès de Schedule que le film est dispo à cette date
    # TODO à faire avec requête gRCP

    # si l’utilisateur existe déjà
    for b in bookings:
        if b["userid"] == userid:
            for d in b["dates"]:
                if d["date"] == date:
                    if movieid in d["movies"]:
                        raise GraphQLError("Booking already exists")
                    d["movies"].append(movieid)
                    write(bookings)
                    return b
            # sinon nouvelle date pour l’utilisateur
            b["dates"].append({"date": date, "movies": [movieid]})
            write(bookings)
            return b

    # si l’utilisateur n’existe pas encore -> on le crée
    newbooking = {
        "userid": userid,
        "dates": [
            {
                "date": date, "movies": [movieid]
            }
        ]
    }
    bookings.append(newbooking)
    write(bookings)
    return newbooking

def remove_booking_with_movie_date_user(_, info, user_id, userid, date, movieid):
    is_admin, error = verify_admin(user_id)
    if error:
        return error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    for b in bookings:
        if b["userid"] == userid:
            for d in b["dates"]:
                if d["date"] == date:
                    if movieid in d["movies"]:
                        d["movies"].remove(movieid)
                        write(bookings)
                        return b
                    raise GraphQLError("Movie not found in this booking")
    raise GraphQLError("Booking not found")

def remove_bookings_with_user_id(_, info, user_id, userid):
    is_admin, error = verify_admin(user_id)
    if error:
        return error
    if not is_admin:
        raise GraphQLError("Unauthorized: admin access required")

    global bookings
    new_bookings = [b for b in bookings if b["userid"] != userid]
    if len(new_bookings) == len(bookings):
        raise GraphQLError("User not found")

    bookings = new_bookings
    write(bookings)
    return (f"All bookings removed for userid : {userid}")