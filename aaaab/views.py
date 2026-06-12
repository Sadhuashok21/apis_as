from django.http import JsonResponse
from .models import *
from django.views import View
from django.utils import timezone
from shared_lib.utils import insertions, random
import random
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg, OuterRef, Subquery, F, ExpressionWrapper, FloatField

# Create your views here.
def index(request):
    products = Products.objects.filter(status="approved")

    data = {
        "status" : True,
        "message": "success",
        "products": list(products.values()),
    }
    return JsonResponse(data, safe=False)


def home(request):
    products = Products.objects.filter(status="approved")

    context = {
        "products" : list(products.values()),
    }

    return JsonResponse(context, safe=False)

def feature(request):

    data = {
        "status": True,
        "message": "success",
    }

    products = Products.objects.filter(
        status="approved",
        feature=1
    ).prefetch_related("productImages").order_by('?')[:1]

    if products.exists():

        product_list = []

        for product in products:

            image_obj = product.productImages.first()

            product_list.append({
                "product_id": product.product_id,
                "name": product.name,
                "price": product.price,
                "discount": product.discount,
                "stock": product.stock,
                "unit": product.unit,
                "image": image_obj.image if image_obj else "",
            })

        data.update({"products": product_list})

    else:
        data.update({"products": "no"})

    return JsonResponse(data)


def product(request):
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if product_id:
        image_subquery = productImages.objects.filter(product_id=OuterRef('product_id')).values('image')[:1]

        product = Products.objects.filter(product_id=product_id, status="approved").annotate(
            avg_rating=Avg("productRatings__rating"),
            image=Subquery(image_subquery)
        )

        ex_pr = product.first()
        if ex_pr:
            data.update({"products": list(product.values("name", "price", "discount", "unit", "stock", "product_id", "image", "avg_rating", "description"))})
        else:
            data.update({"products": "no"})


    else:    
        data.update({"products": "empty"})
    return JsonResponse(data, safe=False)

def products(request):

    image_subquery = productImages.objects.filter(
        product_id=OuterRef('product_id')
    ).values('image')[:1]

    
    

    products = Products.objects.filter(status="approved").annotate(
            avg_rating=Avg("productRatings__rating"),
            image=Subquery(image_subquery),

            discount_price = ExpressionWrapper(
                F("price") - (F("price") * F("discount") / 100),
                output_field = FloatField()
            )
            
        ).values(
            "name",
            "price",
            "product_id",
            "discount",
            "status",
            "avg_rating",
            "image",
            "unit",
            "stock",
            "discount_price",
        )
    
    return JsonResponse({
        "status": True,
        "message": "success",
        "products": list(products)
    }, safe=False)


def insert_rating(request):
    product_id = request.GET.get('product_id', '')
    rating = request.GET.get('rating', '')
    user_id = request.GET.get('user_id', '')
    review = request.GET.get('review', '')


    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }
    if product_id and rating and user_id and review and review:

        exists = ProductRatings.objects.filter(user_id=user_id, product_id=product_id, status="approved").first()

        if exists:
            exists.rating = rating
            exists.review = review
            exists.save()
        else:
            rating = ProductRatings.objects.create(
                product_id = product_id,
                rating = rating,
                review = review,
                rating_id = unique_id(),
                user_id = user_id,
                status="approved",
                time= timezone.now(),
            )

        data['data'] = 'inserted'

  
    return JsonResponse(data, safe=False)


def reviews(request):
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }

    if product_id:
        reviews = ProductRatings.objects.filter(product_id=product_id).select_related('user')

        data["reviews"] = []
        for review in reviews:
            data["reviews"].append({
            "rating": review.rating,
            "review": review.review,
            "time": review.time.strftime("%d-%m-%Y %H:%M:%S"),
            "firstname": review.user.firstname,
            "img": review.user.profile,

        })

   
    return JsonResponse(data, safe=False)

def delete_review(request):
    rating_id = request.GET.get('rating_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if rating_id:
        ProductRatings.objects.filter(rating_id=rating_id).delete()

    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe=False)


# address start 

def address(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }
    
    if user_id:
        address = UserAddress.objects.filter(user_id=user_id, status="approved").select_related('user')

        item = []
        for a in address:

            item.append({
                "address_name": a.address_name,
                "address_full": a.address_full,
                "phone": a.user.phone,
                "default": a.default,
                "type": a.type,
                "address_id": a.address_id,

            })
            
        data['address'] = item
            
    else:
        data.update({"data": "empty"})
        

    return JsonResponse(data, safe=False)


def edit_address(request):
    address = request.GET.get('address', '')
    user_id = request.GET.get('user_id', '')
    default = request.GET.get('default', '')
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    name = request.GET.get('name', '')
    type = request.GET.get('type', '')

    data = {
        "status": True,
        "message": "success",
        "address": ["deleted"]
    }

    if user_id and address and default and name:
        exists = UserAddress.objects.filter(user_id=user_id, address_full=address).first()

        if exists:
            
            exists.default = default
            exists.address_full = address
            exists.city = city
            exists.state = state
            exists.address_name = name
            exists.type = type
                   
            exists.save()

            data['address'] = "inserted"
        else:
            insert_address = UserAddress.objects.create(
                default = default,
                address_name = name,
                address_full = address,
                address_id = unique_id(),
                city = city,
                state = state,
                type = type,
                user_id = user_id,
                status="approved",
                time= timezone.now(),
            )

            data['address'] = 'insert'
    else:
        data['address'] = 'empty'

    return JsonResponse(data, safe=False)

def address_particular(request):

    address_id = request.GET.get('address_id', '')

    data = {
        "status": True,
        "message": "success",
    }
    if address_id:
        addr = UserAddress.objects.filter(address_id = address_id).select_related("user")

        if addr.exists():
            for a in addr:
                data.update({
                    "state": a.state,
                    "country": a.country,
                    "phone": a.user.phone,
                    "name": a.user.firstname,
                    "address": a.address_full,
                    "default": a.default,
                    "city": a.city,
                    "type": a.type,
                })

            
        else:
            data.update({"message": "no"})        
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe=False)


def set_default(request):
    address_id = request.GET.get('address_id', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }
    if address_id and user_id:
        address  = UserAddress.objects.filter(status="approved", user_id=user_id, address_id=address_id).first()
        if address:
     
            addr = UserAddress.objects.filter(user_id=user_id)

            for a in addr:
                a.default = False
                a.save()

            address.default = True
            address.save()

            data.update({"action": "success"})

        else:
            data.update({"action": "no"})  
    else:
        data.update({"action": "empty"})

    return JsonResponse(data, safe=False)

def delete_address(request):
    address_id = request.GET.get('address_id', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "address": ["deleted"]
    }

    if address_id and user_id:
        addr = UserAddress.objects.filter(user_id=user_id, address_id = address_id).first()

        if addr:
            addr.delete()
        else:
            data.update({"message": "no"})        
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe=False)

def default_address(request):
    
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "address": []
    }
    if user_id:
        address = UserAddress.objects.filter(user_id=user_id, default=1).first()

        if address:
            data.update({
                "name": address.user.firstname,
                "address_full": address.address_full
            })
        else:
            data.update({"action": "no"})
    else:
        data['address'] = 'empty'

    
    return JsonResponse(data, safe=False)

def insert_address(request):
    address = request.GET.get('address', '')
    user_id = request.GET.get('user_id', '')
    default = request.GET.get('default', "false").lower() == "true"
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    name = request.GET.get('name', '')
    type = request.GET.get('type', '')

    data = {
        "status": True,
        "message": "success",
        "address": []
    }

    if user_id and address and name and city and state and type:
        exists = UserAddress.objects.filter(user_id=user_id, address_full=address).first()

        if not exists:
            insert_address = UserAddress.objects.create(
                default = default,
                address_name = name,
                address_full = address,
                address_id = unique_id(),
                city = city,
                type= type,
                state = state,
                user_id = user_id,
                status="approved",
                time= timezone.now(),
            )

            data['address'] = "inserted"
            data.update({"action": "success"})
        else:
            data['address'] = "exists"
    else:
        data['address'] = 'empty'

    
    return JsonResponse(data, safe=False)

# end address 

# admin panel

def user_orders(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }

    if user_id:
        orders = Orders.objects.filter(user_id=user_id, status="confirmed").values()

        if orders:
            data['orders'] = list(orders)
        
            data['data'] = "fetched"
        else:
            data['data'] = None

    
    return JsonResponse(data, safe=False)


def order_completed(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
    }

    if user_id:
        order = Orders.objects.filter(status="confirmed", user_id=user_id)

        order.status = "completed"
        order.save()

    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe=False)




def upload_product(request):
    name = request.GET.get('name', '')
    discount = request.GET.get('discount', '')
    user_id = request.GET.get('user_id', '')
    price = request.GET.get('price', '')
    distance_price = request.GET.get('distance_price', '')
    image = request.GET.get('image', '')
    category_id = request.GET.get('category_id', '')
    sub_category_id = request.GET.get('sub_category_id', '')
    unit = request.GET.get('unit', '')
    stock = request.GET.get('stock', '')
    description = request.GET.get('description', '')
    
    data = {
        "status": True,
        "message": "success",
        "data": "error",
    }

    if name and discount and user_id and price and category_id and image and unit and stock and description:

        product_id = unique_id()
        
        product = Products.objects.create(
            user_id = user_id,
            name = name,
            price = price,
            discount = discount,
            product_id = product_id,
            category_id = category_id,
            sub_category_id = sub_category_id,
            status = "approved",
            unit = unit,
            description = description,
            stock = stock,
            time = timezone.now(),
        )

        ima = productImages.objects.create(
            product_id = product_id,
            image = image,
            image_id = unique_id(),
            status = "approved",
            time = timezone.now(),

        )
        
        data.update({"data": "inserted"})

    else:    
        data.update({"data": "empty"})
    
    return JsonResponse(data, safe=False)

def check_name(request):
    name = request.GET.get('check_name', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }
    if name:
        product = SubCategory.objects.filter(status="approved", name=name).first()

        if product:
            data.update({"data": "exists"})
        
        else:
            data.update({"data": "inserted"})
        
    return JsonResponse(data, safe=False)


def edit_product(request):
    name = request.GET.get('name', '')
    discount = request.GET.get('discount', '')
    price = request.GET.get('price', '')
    distance_price = request.GET.get('distance_price', '')
    image = request.GET.get('image', '')
    product_id = request.GET.get('product_id', '')
    unit = request.GET.get('unit', '')
    stock = request.GET.get('stock', '')
    description = request.GET.get('description', '')    

    data = {
        "status": True,
        "message": "success",
    }

    if name and discount and price  and product_id and unit and stock:
        
        product =  Products.objects.filter(product_id=product_id).first()

        if product:
            
            product.name = name
            product.discount = discount
            product.price = price
            product.stock = stock
            product.unit =  unit
            # product.distance_price = 
            product.save()

            data.update({
                "products": {
                    "name": product.name,
                    "discount": product.discount,
                    "price": product.price,
                }
            })
            return JsonResponse(data, safe=False)
    
        data.update({"data": "product is not available"})

    else:
        data.update({"data": "empty"})
    return JsonResponse(data, safe=False)

# admin panel end

# signin system

def create_account(request):
    fullname = request.GET.get('fullname', '')
    lastname = request.GET.get('lastname', '')
    email = request.GET.get('email', '')
    phone = request.GET.get('phone', '')

    data = {
        "status": True,
        "message": "success",
    }

    if email:
        ex = Users.objects.filter(email=email, status="disapproved").first()

        if not ex:    
            if fullname and lastname and phone:
                user_id = unique_id()


                otp = random.randint(100000, 999999)
                
                request.session['otp'] = otp
                request.session['email'] = email

                send_mail(
                    "Your OTP Code",
                    f"Your OTP is {otp}. Do not share it with anyone.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )

                user = Users.objects.create(
                    firstname = fullname,
                    lastname = lastname,
                    email = email,
                    password = "",
                    phone = phone,
                    user_type = 'user',
                    user_id = user_id,
                    status="disapproved",
                    time=timezone.now()
                )

                data.update({"signin": user_id, "otp": otp})

        else:
            data.update({"signin": "exists"}) 
    else:
        data.update({"signin": "empty"})
   
    return JsonResponse(data, safe=False)


def create_account_pass(request):
    password = request.GET.get('password', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if password and user_id:

        passw = Users.objects.filter(user_id=user_id).first()

        if passw:
            passw.password = password
            passw.status="approved"
            passw.save()

            
            data.update({"signin": passw.user_id})
        else:
            data.update({"signin": "no"})
    else:
        data.update({"signin": "missing fields"})
    return JsonResponse(data, safe=False)


def create_account_email(request):
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }
    if email and user_id:

        ee = Users.objects.filter(user_id=user_id).first()

        if ee:
            ee.email = email
            ee.save()
            data.update({"signin": ee.user_id})
            return JsonResponse(data, safe=False)
        else:
            data.update({"signin": "no user found"})
            return JsonResponse(data, safe=False)
    else:
        data.update({"signin": "missing fields"})
        return JsonResponse(data, safe=False)



def signin(request):
    email = request.GET.get('email', '')
    password = request.GET.get('password', '')

    data = {
        "status": True,
        "message": "success",
    }

    if email and password:
        exist = Users.objects.filter(email= email, password= password, status="approved").first()
    
        if exist:
            data.update({"signin": exist.user_id, "user_type": exist.user_type})
        
        else:
            data.update({"signin": "no"})

    else:
        data.update({"signin": "empty"})
    return JsonResponse(data, safe=False)
    

def change_password(request):
    password = request.GET.get('password', '')
    email = request.GET.get('email', '')
    
    data = {
        "status": True,
        "message": "success",
    }

    if password and email:
        ex = Users.objects.filter(email=email).first()
        if ex:
            ex.password = password
            ex.save()
            data.update({"signin": "updated"})
        else:
            data.update({"signin": "exists"})
    else:
        data.update({"signin": "empty"})
    return JsonResponse(data, safe=False)


def send_otp(request):
    email = request.GET.get('email', '')

    data = {
        "status": True,
        "message": "success",
    }

    if email:
        exists = Users.objects.filter(status="approved", email=email).first()

        if exists:
            otp = random.randint(100000, 999999)

            send_mail(
                "Your OTP Code",
                f"Your OTP is {otp}. Do not share it with anyone.",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            data.update({"signin": exists.user_id, "otp": otp})
        else:
            data.update({"signin": "no"})
    else:
        data.update({"signin": "empty"})

    return JsonResponse(data, safe=False)



def create_account_address(request):
    address = request.GET.get('address', '')
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    district = request.GET.get('district', '')
    pincode = request.GET.get('pincode', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if address and city and state and district and pincode and user_id:

        address = Users.objects.filter(user_id=user_id).first()

        if address:
            
            address.address = address
            address.state = state
            address.city = city
            address.pincode = pincode
            address.district = district

            address.save()
            

            
            data.update({"user_id": address.user_id})
            return JsonResponse(data, safe=False)
        else:
            data.update({"data": "no user found"})
            return JsonResponse(data, safe=False)
    else:
        data.update({"user_id": "missing fields"})
        return JsonResponse(data, safe=False)


def create_account_address(request):
    address = request.GET.get('address', '')
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    district = request.GET.get('district', '')
    pincode = request.GET.get('pincode', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if address and city and state and district and pincode and user_id:

        address1 = Users.objects.filter(user_id=user_id).first()

        if address1:
            
            address1.address = address
            address1.state = state
            address1.city = city
            address1.pincode = pincode
            address1.district = district

            address.save()
                    
            data.update({"user_id": address.user_id})
            return JsonResponse(data, safe=False)
        else:
            data.update({"data": "no user found"})
            return JsonResponse(data, safe=False)
    else:
        data.update({"user_id": "missing fields"})
        return JsonResponse(data, safe=False)


# end signin system 




# category start

class CategoryUpload(View):

    def get(self, request):
        name = request.GET.get('name', '')

        data = {
            "status": True,
            "message": "success",
        }

        if name:
            ex = ProductCategory.objects.filter(
                status="approved",
                name=name
            ).first()

            if not ex:
                ProductCategory.objects.create(
                    name=name,
                    status="approved",
                    category_id=unique_id(),
                    time=timezone.now(),
                )
                data["data"] = "inserted"
            else:
                data["data"] = "exists"
        else:
            data["status"] = False
            data["message"] = "empty"

        return JsonResponse(data, safe=False)
    

def sub_category(request):
    name = request.GET.get('name', '')
    category_id = request.GET.get('category_id', '')
    image = request.GET.get('image', '')
    status = request.GET.get('status', '')

    data = {
        "status": True,
        "message": "success",
    }


    if name and category_id and image:
        exis = SubCategory.objects.filter(name=name, status="approved").first()

        if not exis:
            SubCategory.objects.create(
                name = name,
                sub_cat_id = unique_id(),
                category_id=category_id,
                img = image,
                status = status,
                time=timezone.now(),
            )

            data.update({"action": "success"})

        else:
            data.update({"action": "exists"})
    else:
        data.update({"action": "empty"})

    return JsonResponse(data, safe=False)

def sub_category_view(request):
    category_id = request.GET.get('category_id', '')

    data = {
            "status": True,
            "message": "success",
        }
    if category_id:
        
        products = SubCategory.objects.filter(status="approved", category_id=category_id)

        if products:

            data.update({"category": list(products.values())})
        else:
            data.update({"action": "no"})
       
    else:
        data.update({"action": "empty"})

    return JsonResponse(data, safe=False)


def view_sub_cat(request):
    data = {
            "status": True,
            "message": "success",
        }
    
    products = SubCategory.objects.filter(status="approved")

    if products:

        data.update({"category": list(products.values())})
    else:
        data.update({"action": "no"})
    

    return JsonResponse(data, safe=False)

def edit_category(request):
    
    category_id = request.GET.get('category_id', '')
    name = request.GET.get('name', '')

    data = {
            "status": True,
            "message": "success",
        }
    if category_id and name:
        cat = ProductCategory.objects.filter(category_id=category_id).first()

        if cat:
            cat.name = name
            cat.save()
            data.update({"message": "updated"})
        else:
            data.update({"message": "no"})
    else:
        data.update({"message": "empty"})   
    return JsonResponse(data, safe=False)

def category_particular(request):
    category_id = request.GET.get('category_id', '')
    data = {
            "status": True,
            "message": "success",
        }
    if category_id:
        cat = ProductCategory.objects.filter(category_id=category_id).first()

        if cat:
            data.update({"action": cat.name})
        else:
            data.update({"message": "no"})
    else:
        data.update({"message": "empty"})   
    return JsonResponse(data, safe=False)




class Category(View):
    def get(self, request):
        
        products = ProductCategory.objects.filter(status="approved")
        data = {
            "status": True,
            "message": "success",
            "category": list(products.values("name", "category_id"))
        }
       
        return JsonResponse(data, safe=False)

def cat_view(request):
    cat_id = request.GET.get('category_id', '')

    data = {
        "status": True,
        "message": "success",
        "category": []
    }

    if cat_id:
        image_subquery = productImages.objects.filter(product_id=OuterRef('product_id')).values('image')[:1]

        cat = Products.objects.filter(sub_category_id=cat_id).annotate(
            avg_rating=Avg("productRatings__rating"),
            image=Subquery(image_subquery)
        )

        if cat:
            data['category'] = list(cat.values())
        else:

            data['category'].append({"action": "no"})
    else:
        
        data['category'].append({"action": "empty"})

    return JsonResponse(data, safe=False)

# category end

def search(request):
    search = request.GET.get('search', '')

    data = {
        "status": True,
        "message": "success",
        "search": []
    }

    if search:
        image_subquery = productImages.objects.filter(product_id=OuterRef('product_id')).values('image')[:1]

        product = Products.objects.filter(status="approved", name__contains=search).annotate(
            avg_rating=Avg("productRatings__rating"),
            image=Subquery(image_subquery)
        )
        
        if product:
            data['search'] = list(product.values("name", "price", "product_id", "category_id", "feature", "avg_rating", "image"))
        else:
            data['search'].append({"action": "no"})

    else:
        data['search'].append({"action": "empty"})

    return JsonResponse(data, safe=False)

# profile start

def profile(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
        "status": True,
        "message": "success",
        "profile": []
    }

    if user_id:   
        
        user = Users.objects.filter(status="approved", user_id=user_id).first()

        if user:
        
            data['profile'].append({
                "action": "success",
                "name": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "user_type": user.user_type,
                "phone": user.phone,
                })
        
        else:
            data['profile'].append({"action": "no"})

    else:
        data['profile'].append({"action": "empty"})
    return JsonResponse(data, safe=False)



def edit_profile(request):
    fullname = request.GET.get('fullname', '')
    lastname = request.GET.get('lastname', '')
    email = request.GET.get('email', '')
    phone = request.GET.get('phone', '')
    user_id = request.GET.get('user_id', '')


    data = {
        "status": True,
        "message": "success",
    }

    if fullname and lastname and email and phone and user_id:
        
        user = Users.objects.filter(user_id=user_id, status="approved").first()

        if user:

            user.fullname = fullname
            user.lastname = lastname
            user.email = email
            user.phone = phone
            user.save()
        
            data.update({"data": "completed"})
        else:

            data.update({"data": "user is not available"})
    else:    
        data.update({"data": "empty"})
    
    return JsonResponse(data, safe=False)

# end profile

def delete_product(request):
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if product_id:
        product = Products.objects.filter(product_id = product_id).first()
        if product:
            product.delete()

        data.update({"data": "deleted"})
    else: 
        data.update({"data": "empty"})
        
    return JsonResponse(data, safe=False)


# cart system
def add_cart(request):
    user_id = request.GET.get('user_id', '')
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }

    if user_id and product_id:

        order = Orders.objects.filter(status="approved", user_id=user_id, product_id = product_id).first()
        

        if order:
            order.quantity += 1
            order.save()
            image = order.product.productImages.filter(status="approved").values_list('image', flat=True).first()

            item = {
                "action": "updated", 
                "name": order.product.name,
                "order_id": order.order_id, 
                "discount": order.product.discount,
                "product": order.product.name,
                "price": order.product.price,
                "unit": order.product.unit,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "image": image
                }
            data['order'].append(item)
        else:
            cre = Orders.objects.create(
                quantity = 1,
                user_id = user_id,                
                order_id = unique_id(),
                product_id = product_id,
                status = "approved",
                time = timezone.now()
            )
           
            order = Orders.objects.select_related('product').prefetch_related('product__productImages').get(id=cre.id)

            image = order.product.productImages.filter(status="approved").values_list('image', flat=True).first()

            item = {
                "action": "added",
                "name": order.product.name,
                "order_id": order.order_id, 
                "discount": order.product.discount,
                "product": order.product.name,
                "price": order.product.price,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "image": image

            }
            data['order'].append(item)

    else:
        
        data['order'].append({"action": "empty"})

    return JsonResponse(data, safe=False)


def decrease_cart(request):
    user_id = request.GET.get('user_id', '')
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }

    if user_id and product_id:

        order = Orders.objects.filter(status="approved", user_id=user_id, product_id = product_id).first()
        
        if order:
            if order.quantity > 1:
                if order.quantity == 1:
                    order.delete()
                else:
                    order.quantity -= 1
                    order.save()

                print("quantity: ", order.quantity)
            else:
                order.delete()
            
            image = order.product.productImages.filter(status="approved").values_list('image', flat=True).first()

            item = {
                "action": "added",
                "name": order.product.name,
                "order_id": order.order_id, 
                "discount": order.product.discount,
                "product": order.product.name,
                "price": order.product.price,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "image": image

            }
            data['order'].append(item)

        else:
            item = {"action": "removed"}
            data['order'].append(item)

    else:
        item = {"action": "empty"}
        
        data['order'].append(item)
    return JsonResponse(data, safe=False)

def carts(request):
    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }

    orders = Orders.objects \
    .select_related('product') \
    .prefetch_related('product__productImages') \

    quan = 0
    if orders:
        
        for order in orders:
            image = order.product.productImages.filter(
            ).values_list('image', flat=True).first()

            item = {
                "order_id": order.order_id,
                "name": order.product.name,
                "product_id": order.product_id,
                "price": order.product.price,
                "discount": order.product.discount,
                "quantity": order.quantity,
                "image": image,
                "unit": order.product.unit,
                "status": order.status,
                "phone": order.user.phone,
                "time": order.time.strftime("%d-%m-%Y %H:%M:%S"),
            }

            quan += order.quantity


            data["order"].append(item)
            data.update({"items": quan})
    else:
        data['order'].append({"action": "db_empty"})

    return JsonResponse(data, safe=False)

def processing_carts(request):
    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }

    orders = Orders.objects.filter(status="confirmed").select_related('product').prefetch_related('product__productImages')

    quan = 0
    if orders:
        
        for order in orders:
            image = order.product.productImages.filter(
            ).values_list('image', flat=True).first()

            item = {
                "order_id": order.order_id,
                "name": order.product.name,
                "product_id": order.product_id,
                "price": order.product.price,
                "discount": order.product.discount,
                "quantity": order.quantity,
                "image": image,
                "unit": order.product.unit,
                "status": order.status,
                "phone": order.user.phone,
                "time": order.time.strftime("%d-%m-%Y %H:%M:%S"),
            }

            quan += order.quantity


            data["order"].append(item)
            data.update({"items": quan})
    else:
        data['order'].append({"action": "db_empty"})

    return JsonResponse(data, safe=False)

def transit_carts(request):
    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }

    orders = Orders.objects \
    .filter(status="approved") \
    .select_related('product') \
    .prefetch_related('product__productImages') \

    quan = 0
    if orders:
        
        for order in orders:
            image = order.product.productImages.filter(
            ).values_list('image', flat=True).first()

            item = {
                "order_id": order.order_id,
                "name": order.product.name,
                "product_id": order.product_id,
                "price": order.product.price,
                "discount": order.product.discount,
                "quantity": order.quantity,
                "image": image,
                "unit": order.product.unit,
                "status": order.status,
                "phone": order.user.phone,
                "time": order.time.strftime("%d-%m-%Y %H:%M:%S"),
            }

            quan += order.quantity


            data["order"].append(item)
            data.update({"items": quan})
    else:
        data['order'].append({"action": "db_empty"})

    return JsonResponse(data, safe=False)

def completed_carts(request):
    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }

    orders = Orders.objects \
    .filter(status="completed") \
    .select_related('product') \
    .prefetch_related('product__productImages') \

    quan = 0
    if orders:
        
        for order in orders:
            image = order.product.productImages.filter(
            ).values_list('image', flat=True).first()

            item = {
                "order_id": order.order_id,
                "name": order.product.name,
                "product_id": order.product_id,
                "price": order.product.price,
                "discount": order.product.discount,
                "quantity": order.quantity,
                "image": image,
                "unit": order.product.unit,
                "status": order.status,
                "phone": order.user.phone,
                "time": order.time.strftime("%d-%m-%Y %H:%M:%S"),
            }

            quan += order.quantity


            data["order"].append(item)
            data.update({"items": quan})
    else:
        data['order'].append({"action": "db_empty"})

    return JsonResponse(data, safe=False)

def cart(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }
    if user_id:
        orders = Orders.objects \
        .select_related('product') \
        .prefetch_related('product__productImages') \
        .filter(status="approved", user_id=user_id)

        quan = 0
        if orders:
            
            for order in orders:
                image = order.product.productImages.filter(
                    status="approved"
                ).values_list('image', flat=True).first()

                item = {
                    "order_id": order.order_id,
                    "name": order.product.name,
                    "product_id": order.product_id,
                    "price": order.product.price,
                    "discount": order.product.discount,
                    "quantity": order.quantity,
                    "image": image,
                    "unit": order.product.unit,
                    "status": order.status,
                }

                quan += order.quantity


                data["order"].append(item)
            data.update({"items": quan})
        else:
            data['order'].append({"action": "db_empty"})

    else:
        data['order'].append({"action": "empty"})

    return JsonResponse(data, safe=False)


def confirm(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }
    if user_id:
        
        orders = Orders.objects.filter(status="approved", user_id=user_id)

        for order in orders:
            product_id = order.product_id
            quantity = order.quantity

            prod = Products.objects.get(product_id=product_id)
            prod.stock -= quantity
            prod.save()

            order.status = "confirmed"
            order.save()

            data['order'].append({
                "items": 6,
                "name": order.product.name,
                "price": order.product.price,
                })

    else:
        data['order'].append({"action": "empty"})

    return JsonResponse(data, safe=False)


def show_cart(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }
    if user_id:
    
        orders = Orders.objects.filter(user_id=user_id).select_related("product")
 
        for order in orders:
            item = {
                "name": order.product.name,
                "product_id": order.product_id,
                "price": order.product.price,
                "discount": order.product.discount,
                "quantity": order.quantity,
                "unit": order.product.unit,
                "status": order.status,
                "time": order.time,
                "order_id": order.order_id,
                "order_address": order.user.firstname,
            }

            data["order"].append(item)
        else:
            data.update({"action": "db_empty"})
    else:
        data.update({"action": "empty"})
    return JsonResponse(data, safe=False)

def delete_order(request):
    product_id = request.GET.get('product_id', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }

    if product_id and user_id:
        order = Orders.objects.filter(product_id=product_id, status="approved", user_id=user_id).first()

        if order:
            order.delete()
        item = {"action": "deleted"}
        data['order'].append(item)

    else:        
        item = {"action": "empty"}
        data['order'].append(item)

       
    return JsonResponse(data, safe=False)
    

def inProductCart(request):
    product_id = request.GET.get('product_id', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }

    if product_id and user_id:
        order = Orders.objects.filter(user_id=user_id, product_id=product_id, status="approved").first()

        if order:
            data.update({
                "qunatity": order.quantity
            })
        else:
            data.update({"action": "no"})
    else:        
        data.update({"action": "empty"})

       
    return JsonResponse(data, safe=False)
    

# end cart



# ticket start

def insert_ticket(request):
    user_id = request.GET.get('user_id', '')
    name = request.GET.get('name', '')
    problem = request.GET.get('problem', '')

    data = {
        "status": True,
        "message": "success",
    }

    if user_id and name and problem:
    
        ticket = Tickets.objects.create(
            name = name,
            ticket = problem,
            user_id = user_id,
            ticket_id = unique_id(),
            status = "approved",
            time = timezone.now()
        )


    else:
        data.update({"message": "empty"})
    return JsonResponse(data, safe=False)
    
    

def delete_ticket(request):
    ticket_id = request.GET.get('ticket_id', '')
    data = {
        "status": True,
        "message": "success",
    }

    if ticket_id:
        ticket = Tickets.objects.filter(status="approved").first()
        if ticket:

            ticket.status = "completed"
            ticket.save()
        else:
            data.update({"message": "no"})
    else:
        data.update({"message": "empty"})
    return JsonResponse(data, safe=False)
    

def tickets(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if user_id:

        tickets = Tickets.objects.filter(status="approved")

        if tickets:
            
            data.update({"tickets": tickets.values()})
        else:
            
            data.update({"message": "empty"})
    else:
        data.update({"message": "empty"})
    return JsonResponse(data, safe=False)
    

# end tickets