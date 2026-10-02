from rest_framework import serializers
from shared_lib.sfs_core.models import *



class BpSerializers(serializers.ModelSerializer):
    class Meta:
        model = BP
        fields = '__all__'