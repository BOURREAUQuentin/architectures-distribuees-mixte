from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType, MutationType
from flask import Flask, request, jsonify, make_response
import time, json, requests
from werkzeug.exceptions import NotFound
from flask_cors import CORS
import resolvers as r

app = Flask(__name__)

CORS(app)

PORT = 3200
HOST = '0.0.0.0'

# création du schéma GraphQL
type_defs = load_schema_from_path('movie.graphql')

query = QueryType()
mutation = MutationType()

movie = ObjectType('Movie')

query.set_field('movie_with_id', r.movie_with_id)
query.set_field('movie_with_title', r.movie_with_title)
query.set_field('movies_json', r.movies_json)

mutation.set_field('add_movie', r.add_movie)
mutation.set_field('update_movie_rate', r.update_movie_rate)
mutation.set_field('remove_movie_with_id', r.remove_movie_with_id)

schema = make_executable_schema(type_defs, movie, query, mutation)

# page d’accueil du service
@app.route("/", methods=['GET'])
def home():
    """
    Home endpoint for the Movie service.

    Returns:
        Response: HTML welcome message.
    """
    return make_response("<h1 style='color:blue'>Welcome to the Movie service!</h1>",200)

# route GraphQL
@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(
                        schema,
                        data,
                        context_value=None,
                        debug=app.debug
                    )
    status_code = 200 if success else 400
    return jsonify(result), status_code

if __name__ == "__main__":
    #p = sys.argv[1]
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
