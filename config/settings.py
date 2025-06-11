import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins de base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Configuration API Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0-pro-vision")

# Configuration traitement
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 8))
MAX_IMAGE_SIZE_MB = float(os.getenv("MAX_IMAGE_SIZE_MB", 1.8))
COMPRESSION_QUALITY = int(os.getenv("COMPRESSION_QUALITY", 85))

# Chemins des dossiers
INPUT_DIR = BASE_DIR / os.getenv("INPUT_DIR", "data/input")
PROCESSED_DIR = BASE_DIR / os.getenv("PROCESSED_DIR", "data/processed")
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "data/output")
ARCHIVE_DIR = BASE_DIR / os.getenv("ARCHIVE_DIR", "data/archive")

# Configuration logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Formats d'images supportés
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}

# Schéma de données attendu pour les produits
PRODUCT_SCHEMA = {
   "nom_produit": "Nom du produit",
   "description_type": "Description/Type du produit", 
   "volume": "Volume/Quantité",
   "prix_fcfa": "Prix en FCFA",
   "code_barres_ean": "Code-barres EAN",
   "code_article": "Code article",
   "source_information": "Source d'information (lisible/estimé)"
}

# Validation des variables obligatoires
if not GOOGLE_API_KEY:
   raise ValueError("GOOGLE_API_KEY doit être défini dans le fichier .env")

# Création des dossiers s'ils n'existent pas
for directory in [DATA_DIR, INPUT_DIR, PROCESSED_DIR, OUTPUT_DIR, ARCHIVE_DIR, LOGS_DIR]:
   directory.mkdir(parents=True, exist_ok=True)