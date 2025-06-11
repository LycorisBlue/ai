import logging
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageOps
import os

from config.settings import MAX_IMAGE_SIZE_MB, COMPRESSION_QUALITY, PROCESSED_DIR
from src.file_manager import FileManager


class ImageProcessor:
    """Processeur d'images pour optimiser les images avant envoi à Gemini"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.file_manager = FileManager()
        self.max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
        self.compression_quality = COMPRESSION_QUALITY
        self.processed_dir = Path(PROCESSED_DIR)
    
    def process_batch(self, image_paths: List[Path]) -> List[Path]:
        """
        Traite un lot d'images (compression et redimensionnement)
        
        Args:
            image_paths (List[Path]): Liste des chemins vers les images
            
        Returns:
            List[Path]: Liste des chemins vers les images traitées
        """
        processed_images = []
        
        self.logger.info(f"🔄 Début du traitement de {len(image_paths)} images")
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                self.logger.info(f"Traitement image {i}/{len(image_paths)}: {image_path.name}")
                processed_path = self._process_single_image(image_path)
                processed_images.append(processed_path)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur lors du traitement de {image_path.name}: {e}")
                continue
        
        self.logger.info(f"✅ {len(processed_images)} images traitées avec succès")
        return processed_images
    
    def _process_single_image(self, image_path: Path) -> Path:
        """
        Traite une seule image
        
        Args:
            image_path (Path): Chemin vers l'image source
            
        Returns:
            Path: Chemin vers l'image traitée
        """
        # Destination dans le dossier processed
        output_path = self.processed_dir / image_path.name
        
        # Vérifier la taille initiale
        initial_size = self.file_manager.get_file_size_mb(image_path)
        self.logger.debug(f"Taille initiale: {initial_size:.2f} Mo")
        
        if initial_size <= MAX_IMAGE_SIZE_MB:
            # Image déjà dans les limites, simple copie
            import shutil
            shutil.copy2(image_path, output_path)
            self.logger.debug(f"Image copiée sans modification: {image_path.name}")
            return output_path
        
        # Compression nécessaire
        compressed_path = self._compress_image(image_path, output_path)
        
        # Vérifier la taille finale
        final_size = self.file_manager.get_file_size_mb(compressed_path)
        self.logger.debug(f"Taille finale: {final_size:.2f} Mo (réduction: {((initial_size - final_size) / initial_size * 100):.1f}%)")
        
        return compressed_path
    
    def _compress_image(self, input_path: Path, output_path: Path) -> Path:
        """
        Compresse une image pour respecter la limite de taille
        
        Args:
            input_path (Path): Chemin vers l'image source
            output_path (Path): Chemin de sortie
            
        Returns:
            Path: Chemin vers l'image compressée
        """
        try:
            # Ouvrir l'image avec PIL
            with Image.open(input_path) as img:
                # Corriger l'orientation basée sur les métadonnées EXIF
                img = ImageOps.exif_transpose(img)
                
                # Convertir en RGB si nécessaire (pour éviter les problèmes avec PNG, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Créer un fond blanc pour les images avec transparence
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionner si nécessaire
                img = self._resize_if_needed(img)
                
                # Sauvegarder avec compression progressive
                quality = self.compression_quality
                temp_path = output_path
                
                # Ajuster la qualité jusqu'à obtenir la taille désirée
                for attempt in range(5):  # Maximum 5 tentatives
                    img.save(
                        temp_path,
                        'JPEG',
                        quality=quality,
                        optimize=True,
                        progressive=True
                    )
                    
                    current_size = self.file_manager.get_file_size_mb(temp_path)
                    
                    if current_size <= MAX_IMAGE_SIZE_MB:
                        self.logger.debug(f"Compression réussie avec qualité {quality}")
                        break
                    
                    # Réduire la qualité pour la prochaine tentative
                    quality = max(20, quality - 15)
                    
                    if attempt == 4:  # Dernière tentative
                        self.logger.warning(f"Impossible de réduire {input_path.name} sous {MAX_IMAGE_SIZE_MB} Mo")
                
                return temp_path
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la compression de {input_path.name}: {e}")
            raise
    
    def _resize_if_needed(self, img: Image.Image, max_dimension: int = 2048) -> Image.Image:
        """
        Redimensionne l'image si elle est trop grande
        
        Args:
            img (Image.Image): Image PIL
            max_dimension (int): Dimension maximale (largeur ou hauteur)
            
        Returns:
            Image.Image: Image redimensionnée si nécessaire
        """
        width, height = img.size
        
        if max(width, height) <= max_dimension:
            return img
        
        # Calculer le ratio de redimensionnement
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.logger.debug(f"Image redimensionnée: {width}x{height} → {new_width}x{new_height}")
        
        return resized_img
    
    def get_image_info(self, image_path: Path) -> dict:
        """
        Récupère les informations d'une image
        
        Args:
            image_path (Path): Chemin vers l'image
            
        Returns:
            dict: Informations sur l'image
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'filename': image_path.name,
                    'size_mb': self.file_manager.get_file_size_mb(image_path),
                    'dimensions': img.size,
                    'mode': img.mode,
                    'format': img.format
                }
        except Exception as e:
            self.logger.error(f"Impossible de lire les infos de {image_path.name}: {e}")
            return {
                'filename': image_path.name,
                'error': str(e)
            }
    
    def validate_processed_images(self, image_paths: List[Path]) -> List[Path]:
        """
        Valide que toutes les images traitées respectent les contraintes
        
        Args:
            image_paths (List[Path]): Liste des images à valider
            
        Returns:
            List[Path]: Liste des images valides
        """
        valid_images = []
        
        for image_path in image_paths:
            try:
                # Vérifier la taille
                size_mb = self.file_manager.get_file_size_mb(image_path)
                if size_mb > MAX_IMAGE_SIZE_MB:
                    self.logger.warning(f"Image trop lourde ignorée: {image_path.name} ({size_mb:.2f} Mo)")
                    continue
                
                # Vérifier que l'image peut être ouverte
                with Image.open(image_path) as img:
                    img.verify()
                
                valid_images.append(image_path)
                
            except Exception as e:
                self.logger.error(f"Image invalide ignorée: {image_path.name} - {e}")
                continue
        
        self.logger.info(f"✅ {len(valid_images)}/{len(image_paths)} images validées")
        return valid_images