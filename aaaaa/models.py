from django.db import models


# Create your models here.
class AAAUsers(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)
    password = models.CharField(max_length=50)
    profile = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=12)
    user_id = models.CharField(max_length=50, unique=True)
    user_type = models.CharField(max_length=10, default="user")
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = "aaaaa_users"



class AAAProductCategory(models.Model):
    name = models.CharField(max_length=50)
    img = models.CharField(max_length=50)
    category_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_product_category'


class AAAProducts(models.Model):
    name = models.CharField(max_length=50)
    price = models.FloatField()
    product_id = models.CharField(max_length=50, unique=True)
    discount = models.IntegerField(default=0)
    category = models.ForeignKey(
        AAAProductCategory,
        db_column = 'category_id',
        to_field = 'category_id',
        on_delete = models.CASCADE,
        related_name = 'category',
    )
    user = models.ForeignKey(
        AAAUsers,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'users',
    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_products'

class AAAUserAddress(models.Model):
    address = models.CharField(max_length=400)
    user = models.ForeignKey(
        AAAUsers,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'user_address',

    )
    address_id = models.CharField(max_length=50)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_user_addresses'


class AAAproductImages(models.Model):
    product = models.ForeignKey(
        AAAProducts,
        to_field = 'product_id',
        db_column = 'product_id',
        on_delete = models.CASCADE,
        related_name = 'productImages',
    )
    image = models.CharField(max_length=50)
    image_id = models.CharField(unique=True, max_length=50)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_images'




class AAAOrders(models.Model):
    order_id = models.CharField(max_length=50)
    quantity = models.IntegerField(default=0)
    product = models.ForeignKey(
        AAAProducts,
        to_field = 'product_id',
        db_column = 'product_id',
        on_delete = models.CASCADE,
        related_name = 'products',
    )
    user_id = models.CharField(max_length=50)
    combiner_key = models.CharField(max_length=50, default=0)
    status = models.CharField(max_length=12)
    ship_status = models.CharField(max_length=15, default="pending")
    ship_info = models.CharField(max_length=10, default="nt")
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_orders'



class AAAProductDetails(models.Model):
    product = models.ForeignKey(
        AAAProducts,
        to_field = 'product_id',
        db_column = 'product_id',
        on_delete = models.CASCADE,
        related_name = 'productsDetails',
    )
    detail = models.CharField(max_length=500)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaaa_product_details'
