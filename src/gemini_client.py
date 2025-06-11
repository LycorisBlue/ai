import logging
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai

from config.settings import GOOGLE_API_KEY, GEMINI_MODEL, BATCH_SIZE, PRODUCT_SCHEMA


class GeminiClient:
    """Client pour l'API Gemini 1.0 Pro Vision"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.batch_size = BATCH_SIZE
        
        # Configuration de l'API Gemini
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY n'est pas configurée")
        
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        
        self.logger.info(f"Client Gemini initialisé avec le modèle: {GEMINI_MODEL}")
    
    def analyze_images(self, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyse toutes les images par lots
        
        Args:
            image_paths (List[Path]): Liste des chemins vers les images
            
        Returns:
            List[Dict]: Liste des résultats d'analyse
        """
        all_results = []
        total_images = len(image_paths)
        
        self.logger.info(f"🧠 Début de l'analyse de {total_images} images par lots de {self.batch_size}")
        
        # Traiter par lots
        for i in range(0, total_images, self.batch_size):
            batch = image_paths[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_images + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"📦 Traitement du lot {batch_num}/{total_batches} ({len(batch)} images)")
            
            try:
                batch_results = self._analyze_batch(batch)
                all_results.extend(batch_results)
                
                self.logger.info(f"✅ Lot {batch_num} terminé avec succès")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur lors du traitement du lot {batch_num}: {e}")
                # Ajouter des résultats vides pour maintenir la correspondance
                for image_path in batch:
                    all_results.append(self._create_error_result(image_path, str(e)))
        
        self.logger.info(f"🎯 Analyse terminée: {len(all_results)} résultats générés")
        return all_results
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _analyze_batch(self, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyse un lot d'images avec retry automatique
        
        Args:
            image_paths (List[Path]): Lot d'images à analyser
            
        Returns:
            List[Dict]: Résultats pour chaque image du lot
        """
        # Préparer les images pour l'API
        image_data = []
        for image_path in image_paths:
            encoded_image = self._encode_image(image_path)
            image_data.append({
                'mime_type': self._get_mime_type(image_path),
                'data': encoded_image
            })
        
        # Créer le prompt
        prompt = self._create_analysis_prompt(len(image_paths))
        
        # Préparer le contenu pour l'API
        content = [prompt]
        for img_data in image_data:
            content.append({
                'mime_type': img_data['mime_type'],
                'data': img_data['data']
            })
        
        try:
            # Appel à l'API Gemini
            response = self.model.generate_content(content)
            
            if not response.text:
                raise ValueError("Réponse vide de l'API Gemini")
            
            # Parser la réponse JSON
            results = self._parse_gemini_response(response.text, image_paths)
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel API: {e}")
            raise
    
    def _encode_image(self, image_path: Path) -> str:
        """
        Encode une image en base64
        
        Args:
            image_path (Path): Chemin vers l'image
            
        Returns:
            str: Image encodée en base64
        """
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erreur lors de l'encodage de {image_path.name}: {e}")
            raise
    
    def _get_mime_type(self, image_path: Path) -> str:
        """
        Détermine le type MIME d'une image
        
        Args:
            image_path (Path): Chemin vers l'image
            
        Returns:
            str: Type MIME
        """
        extension = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.heic': 'image/heic',
            '.heif': 'image/heif'
        }
        return mime_types.get(extension, 'image/jpeg')
    
    def _create_analysis_prompt(self, num_images: int) -> str:
        """
        Crée le prompt d'analyse pour Gemini
        
        Args:
            num_images (int): Nombre d'images dans le lot
            
        Returns:
            str: Prompt formaté
        """
        fields_description = "\n".join([f"- {key}: {desc}" for key, desc in PRODUCT_SCHEMA.items()])
        
        prompt = f"""
Analysez ces {num_images} images de produits et extrayez les informations suivantes pour chaque produit visible.

INFORMATIONS À EXTRAIRE:
{fields_description}

INSTRUCTIONS:
1. Retournez un JSON valide avec un tableau "produits"
2. Chaque produit doit contenir tous les champs demandés
3. Si une information n'est pas visible ou illisible, indiquez "Non détecté"
4. Pour source_information, utilisez "Lisible" si toutes les infos sont claires, "Partiellement lisible" sinon
5. Assurez-vous que le JSON est bien formaté et valide

FORMAT DE RÉPONSE ATTENDU:
{{
  "produits": [
    {{
      "nom_produit": "...",
      "description_type": "...",
      "volume": "...",
      "prix_fcfa": "...",
      "code_barres_ean": "...",
      "code_article": "...",
      "source_information": "Lisible/Partiellement lisible"
    }}
  ]
}}

Analysez maintenant les images et retournez uniquement le JSON demandé.
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Parse la réponse JSON de Gemini
        
        Args:
            response_text (str): Réponse brute de Gemini
            image_paths (List[Path]): Chemins des images analysées
            
        Returns:
            List[Dict]: Résultats parsés
        """
        try:
            # Nettoyer la réponse (supprimer les balises markdown si présentes)
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parser le JSON
            parsed_data = json.loads(cleaned_response)
            
            if 'produits' not in parsed_data:
                raise ValueError("Format de réponse invalide: clé 'produits' manquante")
            
            products = parsed_data['produits']
            
            # Ajouter les métadonnées (nom de fichier, etc.)
            results = []
            for i, product in enumerate(products):
                # Associer chaque produit à une image (si possible)
                if i < len(image_paths):
                    product['nom_fichier'] = image_paths[i].name
                    product['chemin_fichier'] = str(image_paths[i])
                else:
                    product['nom_fichier'] = f"image_inconnue_{i+1}"
                    product['chemin_fichier'] = ""
                
                # Valider les champs obligatoires
                product = self._validate_product_data(product)
                results.append(product)
            
            # Si moins de produits que d'images, créer des entrées vides
            while len(results) < len(image_paths):
                idx = len(results)
                results.append(self._create_empty_result(image_paths[idx]))
            
            return results
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de parsing JSON: {e}")
            self.logger.debug(f"Réponse brute: {response_text[:500]}...")
            # Retourner des résultats vides pour toutes les images
            return [self._create_error_result(img_path, "Erreur de parsing JSON") for img_path in image_paths]
        
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing de la réponse: {e}")
            return [self._create_error_result(img_path, str(e)) for img_path in image_paths]
    
    def _validate_product_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et normalise les données d'un produit
        
        Args:
            product (Dict): Données brutes du produit
            
        Returns:
            Dict: Données validées
        """
        # S'assurer que tous les champs requis existent
        for field in PRODUCT_SCHEMA.keys():
            if field not in product or product[field] is None:
                product[field] = "Non détecté"
        
        # Nettoyer les valeurs
        for key, value in product.items():
            if isinstance(value, str):
                product[key] = value.strip()
            elif value is None:
                product[key] = "Non détecté"
        
        return product
    
    def _create_empty_result(self, image_path: Path) -> Dict[str, Any]:
        """
        Crée un résultat vide pour une image
        
        Args:
            image_path (Path): Chemin de l'image
            
        Returns:
            Dict: Résultat vide
        """
        result = {field: "Non détecté" for field in PRODUCT_SCHEMA.keys()}
        result.update({
            'nom_fichier': image_path.name,
            'chemin_fichier': str(image_path),
            'source_information': 'Non analysé'
        })
        return result
    
    def _create_error_result(self, image_path: Path, error_message: str) -> Dict[str, Any]:
        """
        Crée un résultat d'erreur pour une image
        
        Args:
            image_path (Path): Chemin de l'image
            error_message (str): Message d'erreur
            
        Returns:
            Dict: Résultat d'erreur
        """
        result = {field: "Erreur d'analyse" for field in PRODUCT_SCHEMA.keys()}
        result.update({
            'nom_fichier': image_path.name,
            'chemin_fichier': str(image_path),
            'source_information': f'Erreur: {error_message}',
            'erreur': error_message
        })
        return result
    
    def test_api_connection(self) -> bool:
        """
        Test la connexion à l'API Gemini
        
        Returns:
            bool: True si la connexion fonctionne
        """
        try:
            # Test simple avec du texte
            response = self.model.generate_content("Test de connexion")
            self.logger.info("✅ Connexion API Gemini validée")
            return True
        except Exception as e:
            self.logger.error(f"❌ Échec de connexion API Gemini: {e}")
            return False