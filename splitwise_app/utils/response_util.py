from rest_framework.response import Response
from rest_framework import status


class ResponseHandler:
    @staticmethod
    def success(message="Success", data=None, status_code=status.HTTP_200_OK):
        if data is None:
            data = {}
        response = {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data
        }
        return Response(response, status=status_code)

    @staticmethod
    def failure(message="Failure", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        if data is None:
            data = {}
        response = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data
        }
        return Response(response, status=status_code)

    @staticmethod
    def exception(message="An error occurred", data=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR):
        if data is None:
            data = {}
        response = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data
        }
        return Response(response, status=status_code)
