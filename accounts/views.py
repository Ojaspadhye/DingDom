from django.shortcuts import render
from accounts.services import (AccountServices)
from rest_framework import (viewsets, status)
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from accounts.serializer import (CreateAccountSerializer)
from rest_framework.response import Response

# Create your views here.

class CreateAccount(viewsets.ViewSet):
    parser_classes=[JSONParser]

    @action(methods=["post"], detail=False)
    def create_account(self, request):
        serializer = CreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            obj = AccountServices(validated_data=serializer.validated_data)
            response = obj.create_account()
            
        except Exception as e:
            response = {
                "error": e
            }

        if "error" in response:
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(response, status=status.HTTP_201_CREATED)


class DeactivateAccount(viewsets.ViewSet):
    parser_classes=[JSONParser]

    def deactivate_acount(self, request):
        pass

