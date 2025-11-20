import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# ============================================================================
# CONFIGURATION DES SERVICES (pour appels inter-services)
# ============================================================================

# Service Booking (utilisé dans get_users_from_booking)
BOOKING_HOST = 'booking' if USE_DOCKER else 'localhost'
BOOKING_PORT = int(os.getenv('BOOKING_PORT', 3203))
BOOKING_BASE_URL = f"http://{BOOKING_HOST}:{BOOKING_PORT}"

# Service User (ce service)
USER_HOST = 'user' if USE_DOCKER else 'localhost'
USER_PORT = int(os.getenv('USER_PORT', 3201))
USER_BASE_URL = f"http://{USER_HOST}:{USER_PORT}"

CACHE_TTL = int(os.getenv('CACHE_TTL', 60))  # Time-to-live en secondes