from rest_framework import serializers
from .models import Trains, Stations


class TrainSerializer(serializers.Serializer):
    class Meta:
        model = Trains
        fields = "__all__"


    def create(self, data):
        return Trains.objects.create(**data)


class StationsSerializer(serializers.Serializer):
    class Meta:
        model = Stations
        fields = "__all__"

    def create(self, data):
        return Stations.objects.create(**data)


class TrainStops(serializers.Serializer):
    pass