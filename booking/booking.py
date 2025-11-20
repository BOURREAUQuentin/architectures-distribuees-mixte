from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType, MutationType
from flask import Flask, render_template, request, jsonify, make_response
import requests
import json, time
from flask_cors import CORS
import resolvers as r
import config

app = Flask(__name__)

CORS(app)

# Création du schéma GraphQL
type_defs = load_schema_from_path('booking.graphql')

query = QueryType()
mutation = MutationType()

booking = ObjectType('Booking')
user = ObjectType('User')
date = ObjectType('Date')
movie = ObjectType('Movie')

query.set_field('bookings_json', r.bookings_json)
query.set_field('booking_with_id', r.booking_with_id)
mutation.set_field('add_booking', r.add_booking)
mutation.set_field('remove_booking_with_movie_date_user', r.remove_booking_with_movie_date_user)
mutation.set_field('remove_bookings_with_user_id', r.remove_bookings_with_user_id)
booking.set_field("userid", r.resolve_booking_userid)
booking.set_field("dates", r.resolve_booking_dates)
date.set_field("movies", r.resolve_date_movies)

schema = make_executable_schema(type_defs, query, mutation, booking, user, date, movie)


# page d’accueil du service
@app.route("/", methods=['GET'])
def home():
   """
    Home endpoint
    ---
    responses:
      200:
        description: Welcome message
    """
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

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
   print("Server running in port %s"%(config.BOOKING_PORT))
   app.run(host=config.BOOKING_HOST, port=config.BOOKING_PORT)
