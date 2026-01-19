"""
Common utilities for API responses and error handling.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data, message=None, status_code=status.HTTP_200_OK):
    """
    Return a standardized success response.
    """
    response_data = {
        'success': True,
        'data': data,
    }
    if message:
        response_data['message'] = message
    
    return Response(response_data, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Return a standardized error response.
    """
    response_data = {
        'success': False,
        'message': message,
    }
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)
