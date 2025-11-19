// Script d'initialisation MongoDB
// Ce script est exécuté automatiquement au premier démarrage de MongoDB

// ============================================================================
// BASE DE DONNÉES USERS
// ============================================================================
db = db.getSiblingDB('users_db');

db.users.insertMany([
    {
        "id": "chris_rivers",
        "name": "Chris Rivers",
        "last_active": 1360031010,
        "is_admin": true
    },
    {
        "id": "peter_curley",
        "name": "Peter Curley",
        "last_active": 1360031222,
        "is_admin": false
    },
    {
        "id": "garret_heaton",
        "name": "Garret Heaton",
        "last_active": 1360031425,
        "is_admin": false
    },
    {
        "id": "michael_scott",
        "name": "Michael Scott",
        "last_active": 1360031625,
        "is_admin": false
    },
    {
        "id": "jim_halpert",
        "name": "Jim Halpert",
        "last_active": 1360031325,
        "is_admin": false
    },
    {
        "id": "pam_beesly",
        "name": "Pam Beesly",
        "last_active": 1360031225,
        "is_admin": false
    },
    {
        "id": "dwight_schrute",
        "name": "Dwight Schrute",
        "last_active": 1360031202,
        "is_admin": false
    }
]);

// ============================================================================
// BASE DE DONNÉES MOVIES
// ============================================================================
db = db.getSiblingDB('movies_db');

db.movies.insertMany([
    {
        "id": "a8034f44-aee4-44cf-b32c-74cf452aaaae",
        "title": "The Martian",
        "rating": 7.0,
        "director": "Ridley Scott"
    },
    {
        "id": "39ab85e5-5e8e-4dc5-afea-65dc368bd7ab",
        "title": "Creed",
        "rating": 7.5,
        "director": "Ryan Coogler"
    },
    {
        "id": "276c79ec-a26a-40a6-b3d3-fb242a5947b6",
        "title": "The Hunger Games: Mockingjay - Part 2",
        "rating": 6.5,
        "director": "Francis Lawrence"
    },
    {
        "id": "720d006c-3a57-4b6a-b18f-9b713b073f3c",
        "title": "Spectre",
        "rating": 6.8,
        "director": "Sam Mendes"
    },
    {
        "id": "96798c08-d19b-4986-a05d-7da856efb697",
        "title": "The Danish Girl",
        "rating": 7.1,
        "director": "Tom Hooper"
    },
    {
        "id": "267eedb8-0f5d-42d5-8f43-72426b9fb3e6",
        "title": "Star Wars: The Force Awakens",
        "rating": 7.9,
        "director": "J.J. Abrams"
    },
    {
        "id": "7daf7208-be4d-4944-a3ae-c1c2f516f3e6",
        "title": "The Revenant",
        "rating": 8.0,
        "director": "Alejandro González Iñárritu"
    }
]);

// ============================================================================
// BASE DE DONNÉES BOOKINGS
// ============================================================================
db = db.getSiblingDB('bookings_db');

db.bookings.insertMany([
    {
        "userid": "chris_rivers",
        "dates": [
            {
                "date": "20151201",
                "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6"]
            }
        ]
    },
    {
        "userid": "garret_heaton",
        "dates": [
            {
                "date": "20151201",
                "movies": ["276c79ec-a26a-40a6-b3d3-fb242a5947b6"]
            },
            {
                "date": "20151215",
                "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6"]
            }
        ]
    },
    {
        "userid": "dwight_schrute",
        "dates": [
            {
                "date": "20151201",
                "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6", "7daf7208-be4d-4944-a3ae-c1c2f516f3e6"]
            },
            {
                "date": "20151214",
                "movies": ["a8034f44-aee4-44cf-b32c-74cf452aaaae"]
            }
        ]
    }
]);

// ============================================================================
// BASE DE DONNÉES SCHEDULES
// ============================================================================
db = db.getSiblingDB('schedules_db');

db.schedules.insertMany([
    {
        "date": "20151130",
        "movies": ["720d006c-3a57-4b6a-b18f-9b713b073f3c", "a8034f44-aee4-44cf-b32c-74cf452aaaae"]
    },
    {
        "date": "20151201",
        "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6", "276c79ec-a26a-40a6-b3d3-fb242a5947b6", "39ab85e5-5e8e-4dc5-afea-65dc368bd7ab", "a8034f44-aee4-44cf-b32c-74cf452aaaae"]
    },
    {
        "date": "20151202",
        "movies": ["276c79ec-a26a-40a6-b3d3-fb242a5947b6", "720d006c-3a57-4b6a-b18f-9b713b073f3c", "a8034f44-aee4-44cf-b32c-74cf452aaaae"]
    },
    {
        "date": "20151203",
        "movies": ["276c79ec-a26a-40a6-b3d3-fb242a5947b6", "39ab85e5-5e8e-4dc5-afea-65dc368bd7ab", "a8034f44-aee4-44cf-b32c-74cf452aaaae"]
    },
    {
        "date": "20151214",
        "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6", "276c79ec-a26a-40a6-b3d3-fb242a5947b6", "39ab85e5-5e8e-4dc5-afea-65dc368bd7ab", "a8034f44-aee4-44cf-b32c-74cf452aaaae", "96798c08-d19b-4986-a05d-7da856efb697"]
    },
    {
        "date": "20151215",
        "movies": ["267eedb8-0f5d-42d5-8f43-72426b9fb3e6", "7daf7208-be4d-4944-a3ae-c1c2f516f3e6"]
    }
]);