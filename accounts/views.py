from django.shortcuts import render
from accounts.services import (AccountServices)
from rest_framework import (viewsets, status)
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from accounts.serializer import (CreateAccountSerializer, LoginSerializer)
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

class LoginAccount(viewsets.ViewSet):
    parser_classes = [JSONParser]

    @action(methods=["post"], detail=False)
    def login_account(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            obj = AccountServices(validated_data=serializer.validated_data)
            response = obj.login_account()

        except:
            response = {"error": "Somthing went wrong"}
        
        if "error" in response:
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(response, status=status.HTTP_200_OK)


class DeactivateAccount(viewsets.ViewSet):
    parser_classes=[JSONParser]

    @action(methods=["patch"], detail=True)
    def deactivate_acount(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            obj = AccountServices(id=pk)
            response = obj.deactivate_account()

        except Exception as e:
            response = {"error": "something went wrong"}

        if "error" in response:
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(response, status=status.HTTP_200_OK)



