from rest_framework import serializers
from .models import *



class BpSerializers(serializers.ModelSerializer):
    class Meta:
        model = BP
        fields = '__all__'