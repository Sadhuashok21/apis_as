from django.db import models

# Create your models here.
class Users(models.Model):
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
        db_table = "aaaab_users"

class ProductCategory(models.Model):
    name = models.CharField(max_length=50)
    category_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    available_time = models.CharField(max_length=50, default=1)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_product_category'

class SubCategory(models.Model):
    name = models.CharField(max_length=50)
    img = models.CharField(max_length=50, default=1)
    sub_cat_id = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        ProductCategory,
        db_column="category_id",
        to_field="category_id",
        on_delete=models.CASCADE,
        related_name="sub_cat_id",
    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_sub_category'


class Products(models.Model):
    name = models.CharField(max_length=50)
    price = models.FloatField()
    description = models.TextField(default="Product")
    product_id = models.CharField(max_length=50, unique=True)
    discount = models.IntegerField(default=0)
    category = models.ForeignKey(
        ProductCategory,
        db_column = 'category_id',
        to_field = 'category_id',
        on_delete = models.CASCADE,
        related_name = 'cat',
    ) 
    sub_category = models.ForeignKey(
        SubCategory,
        db_column = 'sub_cat_id',
        to_field = 'sub_cat_id',
        on_delete = models.CASCADE,
        related_name = 'sub_cat',
    )
    sold = models.IntegerField(default=0)
    feature = models.BooleanField(default=0)
    stock = models.IntegerField(default=1)
    unit = models.IntegerField(default=1)

    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'users',
    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()
    

    class Meta:
        managed = True
        db_table = 'aaaab_products'


    

class ProductRatings(models.Model):
    product = models.ForeignKey(
        Products,
        to_field = 'product_id',
        db_column = 'product_id',
        on_delete = models.CASCADE,
        related_name = 'productRatings',
    )
    rating = models.FloatField(default=0)
    review = models.CharField(max_length=1000, default=None)
    rating_id = models.CharField(unique=True, max_length=50)
    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'users_rating',

    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_product_ratings'

class UserAddress(models.Model):
    address_full = models.CharField(max_length=400)
    default = models.BooleanField(default=0)
    address_name = models.CharField(max_length=40, default="Address")
    state = models.CharField(max_length=40, default="state")
    city = models.CharField(max_length=50, default="city")
    country = models.CharField(max_length=50, default="country")
    phone = models.CharField(max_length=25, default="0")
    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'user_address',

    )
    lat = models.FloatField(default=0)
    lon = models.FloatField(default=0)
    type = models.CharField(max_length=50, default="other")
    address_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_user_addresses'


class productImages(models.Model):
    product = models.ForeignKey(
        Products,
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
        db_table = 'aaaab_images'


class Tickets(models.Model):
    name = models.CharField(max_length=50)
    ticket = models.TextField()
    user = models.ForeignKey(
        Users,
        to_field = "user_id",
        db_column = "user_id",
        on_delete = models.CASCADE,
        related_name = 'user_ticket',
    )
    ticket_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_tickets'


class Orders(models.Model):
    order_id = models.CharField(max_length=50, unique=True)
    quantity = models.IntegerField(default=0)
    product = models.ForeignKey(
        Products,
        to_field = 'product_id',
        db_column = 'product_id',
        on_delete = models.CASCADE,
        related_name = 'products',
    )
    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'order_user',

    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_orders'


class OrderConfirm(models.Model):
    order = models.ForeignKey(
        Orders,
        to_field = 'order_id',
        db_column = 'order_id',
        on_delete = models.CASCADE,
        related_name = 'order_confirm',
    )
    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'user_confirm',

    )
    address = models.ForeignKey(
        UserAddress,
        to_field = 'address_id',
        db_column = 'address_id',
        on_delete = models.CASCADE,
        related_name = 'address_confirm',
    )
    
    status = models.CharField(max_length=12)
    time = models.DateTimeField()
    class Meta:
        managed = True
        db_table = 'aaaab_orders_confirm'


class ProductDetails(models.Model):
    product = models.ForeignKey(
        Products,
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
        db_table = 'aaaab_product_details'




class Chat(models.Model):
    user = models.ForeignKey(
        Users,
        to_field = 'user_id',
        db_column = 'user_id',
        on_delete = models.CASCADE,
        related_name = 'user_id_chat',

    )    
    chat_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'aaaab_chat'



class InChat(models.Model):
    chat = models.ForeignKey(
        Chat,
        to_field='chat_id',
        db_column='chat_id',
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        Users,
        to_field='user_id',
        db_column='sender_id',
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    receiver = models.ForeignKey(
        Users,
        to_field='user_id',
        db_column='receiver_id',
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    message = models.TextField()
    time = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'aaaab_inchat'




