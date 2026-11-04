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


class BlueprintSummarySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BP
        fields = [
            'name',
            'image',
            'image_url',
            'fviews',
            'flikes',
            'fdownloads',
            'fshare',
            'comments',
            'bp_id',
        ]

    def get_image_url(self, obj):
        return get_sfs_image_url(obj.image)


class Blueprint21Serializer(serializers.ModelSerializer):
    """
    Serializer for 2.1 endpoints returning blueprint/planet details, author info,
    and associated category tags with CDN image URLs.
    """
    image_url = serializers.SerializerMethodField()
    views = serializers.IntegerField(source='fviews', read_only=True)
    likes = serializers.IntegerField(source='flikes', read_only=True)
    downloads = serializers.IntegerField(source='fdownloads', read_only=True)
    share = serializers.IntegerField(source='fshare', read_only=True)
    user = serializers.SerializerMethodField()
    user__name = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = BP
        fields = [
            'name',
            'image',
            'image_url',
            'views',
            'likes',
            'downloads',
            'share',
            'fviews',
            'flikes',
            'fdownloads',
            'fshare',
            'comments',
            'bp_id',
            'user',
            'user__name',
            'categories',
        ]

    def get_image_url(self, obj):
        return get_sfs_image_url(obj.image)

    def get_user(self, obj):
        if obj.user and hasattr(obj.user, 'name'):
            return obj.user.name or ''
        return ''

    def get_user__name(self, obj):
        return self.get_user(obj)

    def get_categories(self, obj):
        cats = []
        if hasattr(obj, 'bp_category_bp'):
            for cat in obj.bp_category_bp.all():
                if cat.category:
                    cats.append({
                        'name': cat.category.bp_name,
                        'cat_id': cat.category.category_id,
                    })
        return cats
