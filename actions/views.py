from django.shortcuts import render
from rest_framework import (viewsets, status)
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from actions.serializer import (CreateActionSerializer, LogsSerializer, UpdateActionSerializer)
from actions.services import (ActionServices, MoniterLogServices, LogsServices)
from rest_framework.response import Response
from actions.models import PingLogs, Moniter
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
 
        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_201_CREATED)


class UpdateAction(viewsets.ViewSet):
    parser_classes = [JSONParser]

    @action(methods=["patch", "post", "put"], detail=True)
    def update_actions(self, request, pk=None):
        if not Moniter.objects.filter(id=pk).exists():
            raise Moniter.DoesNotExist("The Moniter Dosenot exists")
        
        moniter = Moniter.objects.filter(id=pk).first()

        serilaizer = UpdateActionSerializer(data=request.data)
        serilaizer.is_valid(raise_exception=True)

        response = ActionServices.update_action(data=serilaizer.validated_data, moniter=moniter)

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)


class GetPingLogs(viewsets.ReadOnlyModelViewSet):
    parser_classes = [JSONParser]
    serializer_class = LogsSerializer

    def get_queryset(self):
        moniter_name = self.request.query_params.get("name")

        if not moniter_name:
            return PingLogs.objects.none()

        return LogsServices.get_logs(moniter_name)

