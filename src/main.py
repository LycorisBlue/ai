#!/usr/bin/env python3
"""
Point d'entrée principal pour le traitement d'images avec Gemini Vision
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from config.settings import LOGS_DIR
from src.file_manager import FileManager
from src.image_processor import ImageProcessor
from src.gemini_client import GeminiClient
from src.data_processor import DataProcessor


def setup_logging(session_id: str):
    """Configure le système de logging"""
    # Créer le dossier logs s'il n'existe pas
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    log_file = LOGS_DIR / f"processing_{session_id}.log"
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file


def main():
    """Fonction principale du traitement"""
    # Générer un ID de session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Configuration du logging
    log_file = setup_logging(session_id)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("🚀 DÉMARRAGE DU TRAITEMENT D'IMAGES AVEC GEMINI VISION")
    logger.info(f"📅 Session: {session_id}")
    logger.info(f"📋 Log: {log_file}")
    logger.info("=" * 60)
    
    try:
        # 1. Initialisation des composants
        logger.info("🔧 Initialisation des composants...")
        
        file_manager = FileManager()
        image_processor = ImageProcessor()
        gemini_client = GeminiClient()
        data_processor = DataProcessor()
        
        # 2. Validation de l'environnement
        logger.info("✅ Validation de l'environnement...")
        
        if not file_manager.validate_directories():
            logger.error("❌ Validation des dossiers échouée")
            return 1
        
        if not gemini_client.test_api_connection():
            logger.error("❌ Connexion API Gemini échouée")
            return 1
        
        # 3. Vérification des images d'entrée
        logger.info("📸 Recherche des images à traiter...")
        
        input_images = file_manager.get_input_images()
        if not input_images:
            logger.warning("⚠️  Aucune image trouvée dans le dossier d'entrée")
            logger.info("💡 Placez vos images dans le dossier: data/input/")
            return 0
        
        logger.info(f"📊 {len(input_images)} images trouvées pour traitement")
        
        # 4. Prétraitement des images
        logger.info("🔄 Prétraitement des images...")
        
        processed_images = image_processor.process_batch(input_images)
        if not processed_images:
            logger.error("❌ Aucune image n'a pu être traitée")
            return 1
        
        # Validation des images traitées
        valid_images = image_processor.validate_processed_images(processed_images)
        if not valid_images:
            logger.error("❌ Aucune image valide après traitement")
            return 1
        
        # 5. Analyse avec Gemini
        logger.info("🧠 Analyse des images avec Gemini...")
        
        analysis_results = gemini_client.analyze_images(valid_images)
        if not analysis_results:
            logger.error("❌ Aucun résultat d'analyse obtenu")
            return 1
        
        # 6. Traitement des données
        logger.info("📊 Traitement et nettoyage des données...")
        
        final_data = data_processor.process_results(analysis_results)
        
        # Générer un rapport de synthèse
        summary = data_processor.generate_summary_report(final_data)
        logger.info("📈 Rapport de synthèse:")
        logger.info(f"   Images traitées: {summary.get('total_images', 0)}")
        logger.info(f"   Analyses complètes: {summary.get('images_completes', 0)}")
        logger.info(f"   Analyses partielles: {summary.get('images_partielles', 0)}")
        logger.info(f"   Erreurs: {summary.get('images_erreur', 0)}")
        logger.info(f"   Score moyen: {summary.get('score_moyen', 0):.1f}%")
        logger.info(f"   Taux de succès: {summary.get('taux_succes', 0):.1f}%")
        
        # 7. Génération des fichiers de sortie
        logger.info("📁 Génération des fichiers de sortie...")
        
        output_files = data_processor.generate_output_files(final_data)
        
        logger.info("📋 Fichiers générés:")
        for file_type, file_path in output_files.items():
            logger.info(f"   {file_type.upper()}: {file_path}")
        
        # 8. Archivage des images traitées
        logger.info("📦 Archivage des images traitées...")
        
        archive_folder = file_manager.archive_processed_images(session_id)
        logger.info(f"📂 Images archivées dans: {archive_folder}")
        
        # 9. Nettoyage
        file_manager.clean_processed_dir()
        
        # 10. Finalisation
        logger.info("=" * 60)
        logger.info("✅ TRAITEMENT TERMINÉ AVEC SUCCÈS")
        logger.info(f"📊 {len(final_data)} produits analysés")
        logger.info(f"📁 Résultats disponibles dans: {output_files['excel']}")
        logger.info("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️  Traitement interrompu par l'utilisateur")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Erreur critique lors du traitement: {e}")
        logger.exception("Détails de l'erreur:")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)