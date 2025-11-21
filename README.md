# UE-AD-A1-MIXTE

## Nos choix techniques

Nous avons mis en place un système **admin/user** dans notre architecture microservices de manière à la fois **maintenable**, **performante** et **simple à étendre**.

### Architecture et gestion des accès

- Toutes les routes (endpoints) de chaque microservice commencent par `/<user_id>/...`
- Chaque route vérifie si l'utilisateur est admin en interrogeant le microservice **User** via : `/users/<user_id>/is_admin`
- Un **cache mémoire** (`user_admin_cache`) permet de limiter les appels au microservice User :
    - Le cache contient un booléen `is_admin` avec un timestamp.
    - Si la donnée est trop ancienne (selon la variable `CACHE_TTL`, fixée à 60 secondes), elle est rechargée depuis le microservice `User`.
- Certains endpoints nécessitent le statut **admin** (ajout, suppression, etc.) :  
  si l'utilisateur n'est pas admin, on retourne une réponse `403 Forbidden`.

---

## Rôles des microservices

| Microservice | Type | Rôle principal |
|-------------|------|----------------|
| **User** | REST | Gestion des utilisateurs, vérification des droits admin et gestion de l'authentification. |
| **Movie** | GraphQL | Gestion des films : création, lecture, mise à jour et suppression des informations de films. |
| **Booking** | GraphQL | Gestion des réservations : création, consultation et suppression de réservations. |
| **Schedule** | gRPC | Planification des séances : récupère les films et vérifie les droits admin via User, expose les horaires disponibles. |

---

## Stockage des données

⚠️ **Cette branche (main) utilise des fichiers JSON pour le stockage des données.**

Si vous souhaitez utiliser **MongoDB** comme base de données, consultez la branche `mongodb` du projet.

Les données sont stockées dans des fichiers JSON situés dans les dossiers `databases/` de chaque microservice :
- `user/databases/users.json`
- `movie/databases/movies.json`
- `booking/databases/bookings.json`
- `schedule/databases/times.json`

---

## Prérequis

### Pour Docker (Recommandé)

- **Docker** installé et en fonctionnement
- **Docker Compose** (généralement inclus avec Docker Desktop)

### Pour exécution locale (sans Docker)

- **Python 3.10+** installé
- Le fichier `requirements.txt` à jour

> **Important** : Le microservice `User` doit toujours être lancé, car il est utilisé par tous les autres pour la gestion admin/user.

---

## Option 1 : Lancement avec Docker Compose (Recommandé)

### Démarrage rapide

La méthode la plus simple pour lancer l'ensemble de l'architecture :

```bash
docker-compose up -d --build
```

- `--build` : Force la reconstruction des images Docker
- `-d` : Lance les conteneurs en arrière-plan (mode détaché)

### Vérification des services

Pour voir l'état des conteneurs :

```bash
docker-compose ps
```

### Logs des services

Pour consulter les logs de tous les services :

```bash
docker-compose logs -f
```

Pour un service spécifique :

```bash
docker-compose logs -f user
docker-compose logs -f movie
docker-compose logs -f booking
docker-compose logs -f schedule
```

### Arrêt des services

Pour arrêter les services sans supprimer les conteneurs :

```bash
docker-compose stop
```

Pour arrêter et supprimer l'ensemble des conteneurs, réseaux et volumes :

```bash
docker-compose down -v
```

### URLs d'accès (avec Docker Compose)

- **User** : http://localhost:3201
- **Movie** : http://localhost:3200
- **Booking** : http://localhost:3203
- **Schedule** : localhost:3202 (serveur gRPC)

---

## Option 2 : Lancement manuel avec Dockerfile

Si vous préférez gérer les conteneurs individuellement, suivez cette méthode.

### 1. Création du réseau Docker

Créer un réseau commun pour que les microservices puissent communiquer :

```bash
docker network create microservices-network
```

### 2. Lancement du microservice User

```bash
docker build -t user-app -f user/Dockerfile .
docker run --rm -it --name user --network microservices-network -p 3201:3201 user-app
```

**URLs de test :**
- http://localhost:3201/peter_curley/users/json (utilisateur non-admin)
- http://localhost:3201/chris_rivers/users/json (utilisateur admin)

### 3. Lancement du microservice Movie

```bash
docker build -t movie-app -f movie/Dockerfile .
docker run --rm -it --name movie --network microservices-network -p 3200:3200 movie-app
```

**URL de base :** http://localhost:3200

### 4. Lancement du microservice Booking

```bash
docker build -t booking-app -f booking/Dockerfile .
docker run --rm -it --name booking --network microservices-network -p 3203:3203 booking-app
```

**URL de base :** http://localhost:3203

### 5. Lancement du microservice Schedule

```bash
docker build -t schedule-app -f schedule/Dockerfile .
docker run --rm -it --name schedule --network microservices-network -p 3202:3202 schedule-app
```

**Note :** Schedule communique avec :
- User : http://user:3201
- Movie : http://movie:3200

Le service écoute sur le port 3202 en mode gRPC.

### Arrêt des conteneurs manuels

Pour arrêter un conteneur spécifique :

```bash
docker stop user
docker stop movie
docker stop booking
docker stop schedule
```

Pour nettoyer le réseau :

```bash
docker network rm microservices-network
```

---

## Option 3 : Lancement local (sans Docker)

Cette option permet d'exécuter les microservices directement sur votre machine, utile pour le développement et le débogage.

### Prérequis locaux

1. **Python 3.10+** avec pip

### Environnement virtuel Python (pour exécution locale)

Si vous souhaitez exécuter les services en local (hors Docker), créez d'abord un environnement virtuel Python :

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
# Sur macOS/Linux :
source venv/bin/activate

# Sur Windows :
venv\Scripts\activate

# Installer les dépendances pour tous les services
pip install -r requirements.txt
```

**Note :** L'environnement virtuel doit rester activé pendant l'utilisation locale des services. Pour le désactiver :
```bash
deactivate
```

### Vérification des fichiers de données

Assurez-vous que les fichiers JSON existent dans les dossiers `databases/` :

```bash
ls -la user/databases/users.json
ls -la movie/databases/movies.json
ls -la booking/databases/bookings.json
ls -la schedule/databases/times.json
```

### Lancement des microservices en local

Ouvrez **4 terminaux différents** (un par microservice) :

**Terminal 1 - User Service :**

```bash
cd user
python user.py
```

**Terminal 2 - Movie Service :**

```bash
cd movie
python movie.py
```

**Terminal 3 - Schedule Service :**

```bash
cd schedule
python schedule.py
```

**Terminal 4 - Booking Service :**

```bash
cd booking
python booking.py
```

### URLs d'accès (exécution locale)

- **User** : http://localhost:3201
- **Movie** : http://localhost:3200
- **Booking** : http://localhost:3203
- **Schedule** : localhost:3202 (serveur gRPC)

### Configuration pour l'exécution locale

Les ports par défaut sont configurés dans chaque fichier Python :
- User : port 3201
- Movie : port 3200
- Booking : port 3203
- Schedule : port 3202

---

## Tests des microservices

### Microservice User (REST)

#### Tests avec curl

Récupérer tous les utilisateurs (utilisateur admin) :

```bash
curl http://localhost:3201/chris_rivers/users/json
```

Récupérer tous les utilisateurs (utilisateur non-admin) :

```bash
curl http://localhost:3201/peter_curley/users/json
```

Vérifier si un utilisateur est admin :

```bash
curl http://localhost:3201/users/chris_rivers/is_admin
```

---

### Microservice Movie (GraphQL)

#### Tests avec curl

Requête GraphQL pour récupérer tous les films :

```bash
curl -X POST http://localhost:3200/graphql \
    -H "Content-Type: application/json" \
    -d '{"query": "{ movies_json(user_id:\"chris_rivers\") { id title rating director } }"}'
```

Requête pour récupérer un film spécifique par ID:

```bash
curl -X POST http://localhost:3200/graphql \
    -H "Content-Type: application/json" \
    -d '{"query": "{ movie_with_id(user_id:\"chris_rivers\", id:\"720d006c-3a57-4b6a-b18f-9b713b073f3c\") { id title rating director } }"}'
```

Requête pour récupérer un film spécifique par titre :

```bash
curl -X POST http://localhost:3200/graphql \
    -H "Content-Type: application/json" \
    -d '{"query": "{ movie_with_title(user_id:\"chris_rivers\", title:\"The Good Dinosaur\") { id title rating director } }"}'
```

---

### Microservice Booking (GraphQL)

#### Tests avec curl

Récupérer toutes les réservations :

```bash
curl -X POST http://localhost:3203/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ bookings_json(user_id: \"chris_rivers\") { userid { id name email } dates { date movies { id title director rating } } } }"}'
```

Récupérer les réservations d'un utilisateur spécifique :

```bash
curl -X POST http://localhost:3203/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ booking_with_id(user_id: \"chris_rivers\", id: \"chris_rivers\") { userid { id name email } dates { date movies { id title director rating } } } }"}'
```

Ajouter une réservation pour le film "The Martian" pour le 01/12/2015 (cas fonctionnel) :

```bash
curl --request POST \
  --url http://127.0.0.1:3203/graphql \
  --header 'Content-Type: application/json' \
  --header 'User-Agent: insomnia/11.6.1' \
  --data '{"query":"mutation{\n  add_booking(user_id: \"chris_rivers\", userid:\"chris_rivers\", date: \"20151201\", movieid: \"a8034f44-aee4-44cf-b32c-74cf452aaaae\") {\n    userid {\n\t\t\tid\n\t\t\tname\n\t\t\tlast_active\n\t\t\tis_admin\n\t\t}\n\t\tdates {\n\t\t\tdate\n\t\t\tmovies {\n\t\t\t\ttitle\n\t\t\t}\n\t\t}\n  }\n}"}'
```

Ajouter une réservation pour le film "The Good Dinosaur" pour le 01/12/2015 (cas erreur car le film n'a pas de séance ce jour-là) :

```bash
curl --request POST \
  --url http://127.0.0.1:3203/graphql \
  --header 'Content-Type: application/json' \
  --header 'User-Agent: insomnia/11.6.1' \
  --data '{"query":"mutation{\n  add_booking(user_id: \"chris_rivers\", userid:\"chris_rivers\", date: \"20151201\", movieid: \"720d006c-3a57-4b6a-b18f-9b713b073f3c\") {\n    userid {\n\t\t\tid\n\t\t\tname\n\t\t\tlast_active\n\t\t\tis_admin\n\t\t}\n\t\tdates {\n\t\t\tdate\n\t\t\tmovies {\n\t\t\t\ttitle\n\t\t\t}\n\t\t}\n  }\n}"}'
```

---

### Microservice Schedule (gRPC)

#### Installation de grpcurl

Sur macOS :

```bash
brew install grpcurl
```

Sur Linux ou Windows :

```bash
# Téléchargez depuis https://github.com/fullstorydev/grpcurl/releases
```

#### Tests gRPC

Obtenir les films pour une date sans séances :

```bash
grpcurl -plaintext \
  -import-path schedule/protos \
  -proto schedule.proto \
  -d '{"userId":"chris_rivers","date":"20251001"}' \
  localhost:3202 Schedule/GetMoviesByDate
```

Obtenir les films pour une date avec séances (exemple : 1er décembre 2015) :

```bash
grpcurl -plaintext \
  -import-path schedule/protos \
  -proto schedule.proto \
  -d '{"userId":"chris_rivers","date":"20151201"}' \
  localhost:3202 Schedule/GetMoviesByDate
```

#### Tests avec un client Python

Vous pouvez également créer un client Python pour tester le service gRPC. Exemple :

```python
import grpc
import schedule_pb2
import schedule_pb2_grpc

channel = grpc.insecure_channel('localhost:3202')
stub = schedule_pb2_grpc.ScheduleStub(channel)

request = schedule_pb2.DateRequest(userId="chris_rivers", date="20151201")
response = stub.GetMoviesByDate(request)

print(response)
```

---

## Documentation OpenAPI

Les fichiers de spécification OpenAPI (format YAML) se trouvent dans les dossiers respectifs de chaque microservice :

- **User** : `user/user.yaml`
- **Movie** : `movie/movie.yaml`
- **Booking** : `booking/booking.yaml`
- **Schedule** : pas de fichier car ce n'était pas possible (néanmoins, spécification gRPC dans `schedule/protos/schedule.proto`)

Ces fichiers peuvent être importés dans des outils comme Swagger UI ou Postman pour une documentation interactive.

---

## Tests via Insomnia

Pour faciliter les tests de l'ensemble de l'architecture, nous fournissons un fichier de configuration Insomnia.

### Import du fichier

1. Ouvrez **Insomnia**
2. Cliquez sur **Import/Export** dans le menu
3. Sélectionnez **Import Data**
4. Choisissez le fichier `Insomnia.yaml` à la racine du projet
5. Tous les endpoints seront automatiquement configurés

### Organisation des requêtes

Les requêtes sont organisées par microservice :
- **User** : Endpoints REST pour la gestion des utilisateurs
- **Movie** : Requêtes GraphQL pour la gestion des films
- **Booking** : Requêtes GraphQL pour la gestion des réservations
- **Schedule** : Requêtes gRPC pour la planification

### Configuration spécifique pour gRPC (Schedule)

Pour les requêtes gRPC du microservice Schedule, vous devez configurer manuellement le fichier proto :

**Pour chaque requête gRPC** dans Insomnia :
- Sélectionnez la requête Schedule dans la liste
- Dans l'onglet **Proto File**, cliquez sur **Add Proto File**
- Sélectionnez le fichier `schedule/protos/schedule.proto` depuis votre projet
- Dans le champ **Method**, sélectionnez la méthode correspondant au nom de la requête :
    - Pour la requête "GetMoviesByDate" → Méthode : `Schedule/GetMoviesByDate`
    - Pour toute autre requête du service Schedule → Méthode : `Schedule/NomDeLaMethode`

---

## Dépannage

### Les conteneurs ne démarrent pas

Vérifiez que les ports ne sont pas déjà utilisés :

```bash
lsof -i :3200
lsof -i :3201
lsof -i :3202
lsof -i :3203
```

### Erreurs de communication entre microservices

Assurez-vous que tous les conteneurs sont sur le même réseau :

```bash
docker network inspect microservices-network
```

### Problèmes de cache admin

Si vous rencontrez des problèmes avec le cache admin, redémarrez le microservice User :

```bash
docker-compose restart user
# ou
docker restart user
```

### Erreurs lors de l'exécution locale

```bash
# Vérifier les dépendances Python
pip list | grep -E "flask|graphene|grpc"

# Vérifier que les ports sont disponibles
netstat -an | grep -E "3200|3201|3202|3203"

# Vérifier que les fichiers JSON sont présents
ls -la */databases/*.json
```

### Fichiers JSON corrompus

Si les fichiers JSON sont corrompus, vous pouvez les restaurer depuis les sauvegardes ou les réinitialiser manuellement. Assurez-vous que chaque fichier respecte la structure JSON valide.

---

## Auteurs

**BOURREAU Quentin / KOWALSKI Damien** - FIL A1