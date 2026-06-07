from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CtscanConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ctscan'
    verbose_name = 'CT Scan & Analyse IA'

    def ready(self):
        import sys
        if 'migrate' in sys.argv or 'test' in sys.argv or 'makemigrations' in sys.argv:
            return
        try:
            from ctscan.inference import get_model
            get_model()
        except Exception as e:
            logger.error(f"[TiCNet] Erreur chargement modèle au démarrage : {e}")