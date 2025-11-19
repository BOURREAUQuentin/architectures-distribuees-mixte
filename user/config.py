import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ============================================================================
# CONFIGURATION MONGODB
# ============================================================================

MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_USER = os.getenv('MONGO_USER', 'admin')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'secretpassword')

# Nom de la base de données spécifique au service User
MONGO_DB_NAME = 'users_db'

# URI de connexion MongoDB
MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"

# ============================================================================
# CONFIGURATION DES SERVICES (pour appels inter-services)
# ============================================================================

# Service Booking (utilisé dans get_users_from_booking)
BOOKING_HOST = 'booking'
BOOKING_PORT = int(os.getenv('BOOKING_PORT', 3203))
BOOKING_BASE_URL = f"http://{BOOKING_HOST}:{BOOKING_PORT}"

# Service User (ce service)
USER_HOST = 'user'
USER_PORT = int(os.getenv('USER_PORT', 3201))
USER_BASE_URL = f"http://{USER_HOST}:{USER_PORT}"

CACHE_TTL = int(os.getenv('CACHE_TTL', 60))  # Time-to-live en secondes