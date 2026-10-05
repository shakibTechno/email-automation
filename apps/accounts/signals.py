"""
Signals for accounts app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for user creation.
    Perform post-creation tasks like sending welcome email.
    """
    if created:
        logger.info(f"New user created: {instance.email}")
        # TODO: Send welcome email
        # TODO: Create email verification token
        # TODO: Send verification email
