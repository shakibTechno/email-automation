"""
Custom exception handlers for the application.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response format
        custom_response_data = {
            'error': True,
            'message': get_error_message(exc),
            'details': response.data if isinstance(response.data, dict) else {'detail': response.data},
            'status_code': response.status_code,
        }
        response.data = custom_response_data

        # Log the error
        logger.error(
            f"API Error: {custom_response_data['message']} - "
            f"Status: {response.status_code} - "
            f"Path: {context['request'].path}"
        )

    else:
        # Handle Django's built-in exceptions
        if isinstance(exc, Http404):
            custom_response_data = {
                'error': True,
                'message': 'Resource not found',
                'details': {'detail': str(exc)},
                'status_code': status.HTTP_404_NOT_FOUND,
            }
            response = Response(custom_response_data, status=status.HTTP_404_NOT_FOUND)

        elif isinstance(exc, PermissionDenied):
            custom_response_data = {
                'error': True,
                'message': 'Permission denied',
                'details': {'detail': str(exc)},
                'status_code': status.HTTP_403_FORBIDDEN,
            }
            response = Response(custom_response_data, status=status.HTTP_403_FORBIDDEN)

        else:
            # Log unexpected errors
            logger.exception(f"Unexpected error: {str(exc)}")
            custom_response_data = {
                'error': True,
                'message': 'An unexpected error occurred',
                'details': {'detail': 'Internal server error'},
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
            response = Response(
                custom_response_data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return response


def get_error_message(exc):
    """
    Extract a user-friendly error message from the exception.
    """
    if isinstance(exc, ValidationError):
        return 'Validation error'
    elif hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict):
            return 'Validation error'
        return str(exc.detail)
    return str(exc)
