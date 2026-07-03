from django.shortcuts import render
from rest_framework import (viewsets, status)
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from actions.serializer import (CreateActionSerializer, LogsSerializer, UpdateActionSerializer)
from actions.services import (ActionServices, MoniterLogServices, LogsServices, AccountService, CheckUser)
from rest_framework.response import Response
from actions.models import PingLogs, Moniter
from rest_framework.exceptions import PermissionDenied, NotFound
from accounts.models import UserAccount
from django.shortcuts import get_object_or_404
import logging

# Create your views here.

logger = logging.getLogger("services")


class CreateAction(viewsets.ViewSet):
    parser_classes=[JSONParser]
    permission_classes=[AllowAny, IsAuthenticated]

    @action(methods=['post'], detail=False)
    def create_action(self, request):
        serializer = CreateActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            obj = ActionServices(data=serializer.validated_data, user=request.user)
            response = obj.create_action()
        
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


class DeactivateAction(viewsets.ViewSet):
    parser_classes = [JSONParser]

    @action(methods=["patch"], detail=True)
    def deactivate_actions(self, request, pk=None):
        if not pk:
            return Response({"error": "id not mentioned"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not Moniter.objects.filter(id=pk).exists():
            return Response({
                "error": "Object Not Found"
            },
            status=status.HTTP_404_NOT_FOUND
        )
        
        response = ActionServices.deactivate_actions(pk=pk)

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)

class GetPingLogs(viewsets.ReadOnlyModelViewSet):
    parser_classes = [JSONParser]
    serializer_class = LogsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        moniter_name = self.request.query_params.get("name")
        user = self.request.user

        action = AccountService.objects.filter(id=moniter_name).first()
        if not action:
            raise NotFound("No item found with this name")
        
        user = CheckUser(user=user, action=action)
        
        if not user.check_useractions():
            raise PermissionDenied("You cannot change bits in this")

        action = get_object_or_404(AccountService, id=moniter_name)

        if not action:
            return AccountService.objects.none()
        
        obj = LogsServices(action=action, user=user)
        print(obj.get_logs)
        return obj.get_logs()

