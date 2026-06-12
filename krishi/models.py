# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class KrishiCart(models.Model):
    id = models.BigAutoField(primary_key=True)
    cart_id = models.CharField(unique=True, max_length=50)
    status = models.CharField(max_length=15)
    time = models.DateTimeField()
    product = models.ForeignKey('KrishiProducts', models.DO_NOTHING, to_field='product_id')
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')
    quantity = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'krishi_cart'


class KrishiCrop(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    soil_type = models.CharField(max_length=50)
    season = models.CharField(max_length=20)
    water_need = models.CharField(max_length=20)
    climate = models.CharField(max_length=30)
    profit_min = models.IntegerField()
    profit_max = models.IntegerField()
    suitable_district = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'krishi_crop'


class KrishiImages(models.Model):
    id = models.BigAutoField(primary_key=True)
    image = models.CharField(max_length=50)
    image_id = models.CharField(unique=True, max_length=50)
    time = models.DateTimeField()
    product = models.ForeignKey('KrishiProducts', models.DO_NOTHING, to_field='product_id')
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')

    class Meta:
        managed = False
        db_table = 'krishi_images'


class KrishiLiveMandi(models.Model):
    id = models.BigAutoField(primary_key=True)
    state = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    market = models.CharField(max_length=50)
    commodity = models.CharField(max_length=50)
    variety = models.CharField(max_length=50)
    grade = models.CharField(max_length=50)
    arrival_date = models.DateField()
    min_price = models.FloatField()
    max_price = models.FloatField()
    modal_price = models.FloatField()
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'krishi_live_mandi'
        unique_together = (('state', 'district', 'market', 'commodity', 'variety', 'grade', 'arrival_date'),)


class KrishiProductAvailable(models.Model):
    id = models.BigAutoField(primary_key=True)
    available = models.IntegerField()
    status = models.CharField(max_length=12)
    time = models.DateTimeField()
    product = models.ForeignKey('KrishiProducts', models.DO_NOTHING, to_field='product_id')
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')

    class Meta:
        managed = False
        db_table = 'krishi_product_available'


class KrishiProductDetails(models.Model):
    id = models.BigAutoField(primary_key=True)
    detail = models.CharField(max_length=500)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()
    product = models.ForeignKey('KrishiProducts', models.DO_NOTHING, to_field='product_id')
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')

    class Meta:
        managed = False
        db_table = 'krishi_product_details'


class KrishiProductRatings(models.Model):
    id = models.BigAutoField(primary_key=True)
    rating = models.IntegerField()
    rating_id = models.CharField(unique=True, max_length=50)
    time = models.DateTimeField()
    product = models.ForeignKey('KrishiProducts', models.DO_NOTHING, to_field='product_id')
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')

    class Meta:
        managed = False
        db_table = 'krishi_product_ratings'


class KrishiProducts(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    price = models.FloatField()
    discount = models.IntegerField()
    quantity = models.IntegerField()
    harvest_date = models.DateField(blank=True, null=True)
    image = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    product_id = models.CharField(unique=True, max_length=50)
    time = models.DateTimeField()
    user = models.ForeignKey('KrishiUsers1', models.DO_NOTHING, to_field='user_id')
    status = models.CharField(max_length=12)

    class Meta:
        managed = False
        db_table = 'krishi_products'


class KrishiUsers1(models.Model):
    id = models.BigAutoField(primary_key=True)
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    email = models.CharField(max_length=254)
    password = models.CharField(max_length=50)
    profile = models.CharField(max_length=100)
    address1 = models.CharField(max_length=50)
    address2 = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=12)
    user_id = models.CharField(unique=True, max_length=50)
    user_type = models.CharField(max_length=10)
    is_verified = models.IntegerField()
    time = models.DateTimeField()
    farm_name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'krishi_users1'
