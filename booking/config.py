import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# ============================================================================
# CONFIGURATION MONGODB
# ============================================================================

MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_USER = os.getenv('MONGO_USER', 'admin')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'password')

# Nom de la base de données spécifique au service Booking
MONGO_DB_NAME = 'bookings_db'

# URI de connexion MongoDB
MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"

# ============================================================================
# CONFIGURATION DES SERVICES (pour appels inter-services)
# ============================================================================

# Service User (nécessaire pour vérifier les droits admin)
USER_HOST = 'user' if USE_DOCKER else 'localhost'
USER_PORT = int(os.getenv('USER_PORT', 3201))
USER_BASE_URL = f"http://{USER_HOST}:{USER_PORT}"

# Service Movie (nécessaire pour récupérer les détails des films)
MOVIE_HOST = 'movie' if USE_DOCKER else 'localhost'
MOVIE_PORT = int(os.getenv('MOVIE_PORT', 3200))
MOVIE_BASE_URL = f"http://{MOVIE_HOST}:{MOVIE_PORT}"

# Service Schedule (gRPC)
SCHEDULE_HOST = 'schedule' if USE_DOCKER else 'localhost'
SCHEDULE_PORT = int(os.getenv('SCHEDULE_PORT', 3202))
SCHEDULE_GRPC_URL = f"{SCHEDULE_HOST}:{SCHEDULE_PORT}"

# Service Booking (ce service)
BOOKING_HOST = 'booking' if USE_DOCKER else 'localhost'
BOOKING_PORT = int(os.getenv('BOOKING_PORT', 3203))

CACHE_TTL = int(os.getenv('CACHE_TTL', 60))  # Time-to-live en secondes