from django.apps import AppConfig
from django.db.models.signals import post_migrate


def app_wheel_initiater(sender, **kwargs):
    from actions.schedulers import base_wheel
    import logging
    
    logger = logging.getLogger(__name__)

    try:
        logger.info("The db is migrated. Time wheel starts")
        base_wheel()
        logger.info("Woooooooooo!! base wheel starts")
    
    except Exception as e:
        logger.warning(e)



class ActionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'actions'

    def ready(self):
        post_migrate.connect(app_wheel_initiater, sender=self)
