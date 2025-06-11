import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from config.settings import (
   INPUT_DIR, PROCESSED_DIR, OUTPUT_DIR, ARCHIVE_DIR,
   SUPPORTED_IMAGE_FORMATS
)


class FileManager:
   """Gestionnaire des fichiers et dossiers pour le traitement d'images"""
   
   def __init__(self):
       self.logger = logging.getLogger(__name__)
       self.input_dir = Path(INPUT_DIR)
       self.processed_dir = Path(PROCESSED_DIR)
       self.output_dir = Path(OUTPUT_DIR)
       self.archive_dir = Path(ARCHIVE_DIR)
   
   def get_input_images(self) -> List[Path]:
       """
       Récupère toutes les images valides du dossier d'entrée
       
       Returns:
           List[Path]: Liste des chemins vers les images valides
       """
       if not self.input_dir.exists():
           self.logger.error(f"Le dossier d'entrée n'existe pas : {self.input_dir}")
           return []
       
       images = []
       for file_path in self.input_dir.iterdir():
           if file_path.is_file() and self._is_valid_image(file_path):
               images.append(file_path)
               self.logger.debug(f"Image valide trouvée : {file_path.name}")
           elif file_path.is_file():
               self.logger.warning(f"Fichier ignoré (format non supporté) : {file_path.name}")
       
       self.logger.info(f"📸 {len(images)} images valides trouvées dans {self.input_dir}")
       return sorted(images)
   
   def _is_valid_image(self, file_path: Path) -> bool:
       """
       Vérifie si un fichier est une image supportée
       
       Args:
           file_path (Path): Chemin vers le fichier
           
       Returns:
           bool: True si l'image est supportée
       """
       return file_path.suffix.lower() in SUPPORTED_IMAGE_FORMATS
   
   def move_to_processed(self, image_path: Path) -> Path:
       """
       Déplace une image vers le dossier processed
       
       Args:
           image_path (Path): Chemin de l'image source
           
       Returns:
           Path: Nouveau chemin de l'image
       """
       destination = self.processed_dir / image_path.name
       
       # Éviter les conflits de noms
       counter = 1
       while destination.exists():
           stem = image_path.stem
           suffix = image_path.suffix
           destination = self.processed_dir / f"{stem}_{counter}{suffix}"
           counter += 1
       
       shutil.move(str(image_path), str(destination))
       self.logger.debug(f"Image déplacée : {image_path.name} → {destination.name}")
       return destination
   
   def archive_processed_images(self, session_id: Optional[str] = None) -> Path:
       """
       Archive les images traitées dans un dossier horodaté
       
       Args:
           session_id (str, optional): Identifiant de session personnalisé
           
       Returns:
           Path: Chemin du dossier d'archive créé
       """
       if session_id is None:
           session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
       
       archive_folder = self.archive_dir / f"session_{session_id}"
       archive_folder.mkdir(parents=True, exist_ok=True)
       
       # Compter les fichiers à archiver
       files_to_archive = list(self.processed_dir.glob("*"))
       if not files_to_archive:
           self.logger.info("Aucun fichier à archiver dans le dossier processed")
           return archive_folder
       
       # Déplacer tous les fichiers du dossier processed vers l'archive
       for file_path in files_to_archive:
           if file_path.is_file():
               destination = archive_folder / file_path.name
               shutil.move(str(file_path), str(destination))
       
       self.logger.info(f"📦 {len(files_to_archive)} fichiers archivés dans {archive_folder}")
       return archive_folder
   
   def clean_processed_dir(self):
       """Nettoie le dossier processed de tous ses fichiers"""
       files_cleaned = 0
       for file_path in self.processed_dir.glob("*"):
           if file_path.is_file():
               file_path.unlink()
               files_cleaned += 1
       
       if files_cleaned > 0:
           self.logger.info(f"🧹 {files_cleaned} fichiers supprimés du dossier processed")
   
   def get_latest_output_files(self) -> List[Path]:
       """
       Récupère les derniers fichiers de sortie générés
       
       Returns:
           List[Path]: Liste des fichiers de sortie récents
       """
       output_files = []
       for file_path in self.output_dir.glob("*"):
           if file_path.is_file() and file_path.suffix in {'.csv', '.xlsx'}:
               output_files.append(file_path)
       
       # Trier par date de modification (plus récent en premier)
       output_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
       return output_files
   
   def create_session_id(self) -> str:
       """
       Génère un identifiant unique pour la session de traitement
       
       Returns:
           str: Identifiant de session au format YYYYMMDD_HHMMSS
       """
       return datetime.now().strftime("%Y%m%d_%H%M%S")
   
   def get_file_size_mb(self, file_path: Path) -> float:
       """
       Retourne la taille d'un fichier en Mo
       
       Args:
           file_path (Path): Chemin vers le fichier
           
       Returns:
           float: Taille en Mo
       """
       if not file_path.exists():
           return 0.0
       
       size_bytes = file_path.stat().st_size
       return size_bytes / (1024 * 1024)
   
   def validate_directories(self) -> bool:
       """
       Valide que tous les dossiers nécessaires existent
       
       Returns:
           bool: True si tous les dossiers sont valides
       """
       directories = [self.input_dir, self.processed_dir, self.output_dir, self.archive_dir]
       
       for directory in directories:
           if not directory.exists():
               self.logger.error(f"Dossier manquant : {directory}")
               return False
           
           if not directory.is_dir():
               self.logger.error(f"Le chemin n'est pas un dossier : {directory}")
               return False
       
       self.logger.info("✅ Tous les dossiers sont valides")
       return True