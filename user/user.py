from flask import Flask, render_template, request, jsonify, make_response
import json, time, os
import requests
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import config

app = Flask(__name__)

CORS(app)

# cache local pour stocker si un user est admin
# format : { "user_id": {"is_admin": True/False, "timestamp": 123456789} }
user_admin_cache = {}

# Connexion MongoDB
client = MongoClient(config.MONGO_URI)
db = client[config.MONGO_DB_NAME]
users_collection = db['users']

# Helper pour convertir ObjectId en string dans les réponses
def serialize_user(user):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if user and '_id' in user:
        user['_id'] = str(user['_id'])
    return user

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
            return False, make_response(jsonify({"error": "Unable to verify user"}), 401)
    except requests.exceptions.RequestException:
        return False, make_response(jsonify({"error": "User service unreachable"}), 503)

# vérifie si un utilisateur est admin à partir de son ID
@app.route("/users/<user_id>/is_admin", methods=['GET'])
def is_admin(user_id):
    """
    Check if a user is an admin based on their ID.

    Args:
        user_id (str): ID of the user to check.

    Returns:
        Response: JSON response with user's ID and admin status,
                  or error if the user is not found.
    """
    user = users_collection.find_one({"id": user_id})

    if user:
        print("user trouvé dans microservice User")
        return jsonify({
            "id": user["id"],
            "is_admin": user.get("is_admin", False)
        }), 200

    return jsonify({"error": "User ID not found"}), 404

# page d'accueil du service
@app.route("/", methods=['GET'])
def home():
    """
    Home endpoint for the User service.

    Returns:
        str: HTML welcome message.
    """
    return "<h1 style='color:blue'>Welcome to the User service!</h1>"

# retourne tous les utilisateurs en JSON brut
@app.route("/<user_id>/users/json", methods=['GET'])
def get_json(user_id):
    """
    Retrieve all users in raw JSON format.

    Args:
        user_id (str): ID of the requesting user.

    Returns:
        Response: JSON response containing all users if the requester is admin,
                  otherwise an unauthorized error.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    users = list(users_collection.find({}))
    for user in users:
        user['_id'] = str(user['_id'])

    return jsonify(users)

# retourne un utilisateur à partir de son ID
@app.route("/<user_id>/users/<user_id_wanted>", methods=['GET'])
def get_user_by_id(user_id, user_id_wanted):
    """
    Retrieve a user by their ID.

    Args:
        user_id (str): ID of the requesting user.
        user_id_wanted (str): ID of the user to retrieve.

    Returns:
        Response: JSON response with user details if found and requester is admin,
                  or error if user not found or unauthorized.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    user = users_collection.find_one({"id": user_id_wanted})

    if user:
        return jsonify(serialize_user(user)), 200

    return jsonify({"error": "User ID not found"}), 404

# retourne un utilisateur à partir de son nom
@app.route("/<user_id>/users/by_name", methods=['GET'])
def get_user_by_name(user_id):
    """
    Retrieve a user by their name.

    Args:
        user_id (str): ID of the requesting user.

    Query Parameters:
        name (str): Name of the user to search for.

    Returns:
        Response: JSON response with user details if found and requester is admin,
                  otherwise an error message.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    if not request.args or 'name' not in request.args:
        return make_response(jsonify({"error": "Name parameter required"}), 400)

    name = request.args.get('name')
    user = users_collection.find_one({"name": name})

    if not user:
        return make_response(jsonify({"error": "User name not found"}), 404)

    return make_response(jsonify(serialize_user(user)), 200)

# récupère les noms des utilisateurs qui ont une réservation d'un film pour une certaine date
@app.route("/<user_id>/users/bookings", methods=["GET"])
def get_users_from_booking(user_id):
    """
    Get the names of users who have booked a specific movie on a given date.

    Args:
        user_id (str): ID of the requesting user.

    Request Body:
        {
            "date": "YYYY-MM-DD",
            "movie": "movie_id"
        }

    Returns:
        Response: JSON list of user names who booked the movie,
                  or error if user not found or unauthorized.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    req = request.get_json()
    date = req.get("date")
    movie_id = req.get("movie")
    user_list = []

    query = """
    query($user_id: String!) {
      bookings_json(user_id: $user_id) {
        userid {
          id
          name
          last_active
          is_admin
        }
        dates {
          date
          movies {
            id
            title
          }
        }
      }
    }
    """
    variables = {"user_id": user_id}

    r = requests.post(
        f"{config.BOOKING_BASE_URL}/graphql",
        json={"query": query, "variables": variables}
    )

    data = r.json().get("data", {}).get("bookings_json", [])

    for b in data:
        for d in b["dates"]:
            if d["date"] == date:
                for m in d["movies"]:
                    if not m:
                        continue
                    if m.get("id") == movie_id:
                        name = b["userid"]["name"]
                        if not name:
                            return make_response(jsonify({"error": "The user does not exist"}), 404)
                        user_list.append(name)
    if not user_list:
        return make_response(jsonify({"error": "No bookings found for the given date and movie"}), 404)

    return make_response(jsonify({
        "users": user_list
    }), 200)

# ajoute un utilisateur
@app.route("/<user_id>/users/<user_id_wanted>", methods=['POST'])
def add_user(user_id, user_id_wanted):
    """
    Add a new user.

    Args:
        user_id (str): ID of the requesting user.
        user_id_wanted (str): ID for the new user.

    Request Body:
        JSON object containing user details (id, name, is_admin).

    Returns:
        Response: JSON message confirming addition,
                  or error if user ID already exists or unauthorized.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    # Vérifier si l'utilisateur existe déjà
    existing_user = users_collection.find_one({"id": user_id_wanted})
    if existing_user:
        return make_response(jsonify({"error": "User ID already exists"}), 400)

    req = request.get_json()
    users_collection.insert_one(req)

    return make_response(jsonify({"message": "User added"}), 200)

# modifie le nom de l'utilisateur à partir de son ID
@app.route("/<user_id>/users/<user_id_wanted>/<name>", methods=['PUT'])
def update_user_name(user_id, user_id_wanted, name):
    """
    Update the name of an existing user by their ID.

    Args:
        user_id (str): ID of the requesting user.
        user_id_wanted (str): ID of the user to update.
        name (str): New name for the user.

    Returns:
        Response: JSON response with updated user info,
                  or error if user not found or unauthorized.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    result = users_collection.find_one_and_update(
        {"id": user_id_wanted},
        {"$set": {"name": name}},
        return_document=True
    )

    if result:
        return make_response(jsonify(serialize_user(result)), 200)

    return make_response(jsonify({"error": "user ID not found"}), 404)

# supprime un utilisateur
@app.route("/<user_id>/users/<user_id_wanted>", methods=['DELETE'])
def delete_user(user_id, user_id_wanted):
    """
    Delete a user by their ID.

    Args:
        user_id (str): ID of the requesting user.
        user_id_wanted (str): ID of the user to delete.

    Returns:
        Response: JSON response confirming deletion,
                  or error if user not found or unauthorized.
    """
    is_admin, error = verify_admin(user_id)
    if error:
        return error

    # si pas admin -> accès interdit
    if not is_admin:
        return make_response(jsonify({"error": "Unauthorized: admin access required"}), 403)

    user = users_collection.find_one_and_delete({"id": user_id_wanted})

    if user:
        return make_response(jsonify(serialize_user(user)), 200)

    return make_response(jsonify({"error": "user ID not found"}), 404)

if __name__ == "__main__":
    app.run(host=config.USER_HOST, port=config.USER_PORT, debug=True)