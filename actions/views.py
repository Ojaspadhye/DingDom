from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from actions.serializer import (CreateActionSerializer)
from actions.services import (ActionServices, MoniterLogServices)
from rest_framework.response import Response
import logging

# Create your views here.

logger = logging.getLogger("services")


class CreateAction(viewsets.ViewSet):
    parser_classes=[JSONParser]
    permission_classes=[AllowAny]

    @action(methods=['post'], detail=False)
    def create_action(self, request):
        serializer = CreateActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = ActionServices.create_action(data=serializer.validated_data)
        
        except Exception as e:
            logger.warning(f"error: {e}")
            response = {
                "error": "Somthing went wrongs"
            }

        return Response(response)


class GetPingLogs(viewsets.ReadOnlyModelViewSet):
    pass

