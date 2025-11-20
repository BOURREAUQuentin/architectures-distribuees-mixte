import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# ============================================================================
# CONFIGURATION DES SERVICES (pour appels inter-services)
# ============================================================================

# Service User (nécessaire pour vérifier les droits admin)
USER_HOST = 'user' if USE_DOCKER else 'localhost'
USER_PORT = int(os.getenv('USER_PORT', 3201))
USER_BASE_URL = f"http://{USER_HOST}:{USER_PORT}"

# Service Movie (ce service)
MOVIE_HOST = 'movie' if USE_DOCKER else 'localhost'
MOVIE_PORT = int(os.getenv('MOVIE_PORT', 3200))

CACHE_TTL = int(os.getenv('CACHE_TTL', 60))  # Time-to-live en secondes