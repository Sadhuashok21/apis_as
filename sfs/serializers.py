from rest_framework import serializers
from .models import BP, BpCat, BPCategories
from apis.cdn_utils import get_sfs_image_url, get_sfs_zip_url


class BpSerializers(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    zip_url = serializers.SerializerMethodField()

    class Meta:
        model = BP
        fields = '__all__'

    def get_image_url(self, obj):
        return get_sfs_image_url(obj.image)

    def get_zip_url(self, obj):
        return get_sfs_zip_url(obj.zipfiles)


class BpCatSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BpCat
        fields = '__all__'

    def get_image_url(self, obj):
        return get_sfs_image_url(obj.bp_img)