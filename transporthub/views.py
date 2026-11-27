from django.shortcuts import render
from .serailizers import TrainSerializer, StationsSerializer
from rest_framework import viewsets
from . import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


# Create your views here.
class Trains(viewsets.ModelViewSet):

    queryset = models.Trains.objects.all()

    serializer_class = TrainSerializer


class Stations(viewsets.ModelViewSet):
    queryset = models.Stations.objects.all()

    serializer_class = StationsSerializer

class TrainsStops(viewsets.ModelViewSet):

    def get(self, request):

        train_id = request.GET.get("train_no", "")

        if train_id:

            self.queryset = models.TrainStops.objects.filter(train_id=train_id).all()

            self.serializer_class = ""
            pass



@api_view(["GET"])
def create_train(request):
    
    serializer = TrainSerializer(data=request.data)


    if serializer.is_valid():
        serializer.save()

        return Response(
            {
                "status": True,
                "message": "Created"
            }
        , status = status.HTTP_200_OK)

    return Response({
        "status": True,
        "mesage": "Not created",
        
        }, status = status.HTTP_400_BAD_REQUEST)