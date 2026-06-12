from django.shortcuts import render
from django.http import JsonResponse
from .models import *
from django.views import View
from django.utils import timezone
from shared_lib.utils import insertions, random
import random
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

from django.db.models import Avg, OuterRef, Subquery

from django.utils.decorators import method_decorator


# Create your views here.
def index(request):

    products = AAAProducts.objects.filter(status="approved")

    data = {
        "status" : True,
        "message": "success",
        "products": list(products.values()),
    }
    return JsonResponse(data, safe=False)


def home(request):
    products = AAAProducts.objects.filter(status="approved")

    context = {
        "status" : True,
        "message": "success",
        "products" : list(products.values()),
    }

    return JsonResponse(context, safe=False)

def product(request):
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if product_id:
        product = AAAProducts.objects.filter(product_id=product_id)

        ex_pr = product.first()
        if ex_pr:
            data.update({"products": list(product.values())})
        else:
            data.update({"products": "no product"})


    else:    
        data.update({"products": "empty"})
    return JsonResponse(data, safe=False)

def products(request):

    image_subquery = AAAproductImages.objects.filter(
        product_id=OuterRef('product_id')
    ).values('image')[:1]

    products = (
        AAAProducts.objects
        .filter(status="approved")
        .annotate(
            avg_rating=Avg("productRatings__rating"),
            image=Subquery(image_subquery)
        )
        .values(
            "name",
            "price",
            "product_id",
            "discount",
            "status",
            "avg_rating",
            "image"
        )
    )

    return JsonResponse({
        "status": True,
        "message": "success",
        "products": list(products)
    }, safe=False)




def address(request):

    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }
    
    if user_id:
        address = UserAddress.objects.filter(user_id=user_id).values()

        data.update({"products": list(address)})
        

    return JsonResponse(data, safe=False)

def insert_address(request):
    address = request.GET.get('address', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }

    if user_id and address:
        exists = UserAddress.objects.filter(user_id=user_id, address=address).first()

        if not exists:
            insert_address = UserAddress.objects.create(
                address = address,
                address_id = random.unique_id(),
                user_id = user_id,
                status="approved",
                time= timezone.now(),
            )

        data['data'] = "inserted"

    
    return JsonResponse(data, safe=False)


def user_orders(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }

    if user_id:
        orders = Orders.objects.filter(user_id=user_id).values()

        if orders:
            data['products'] = list(orders)
        

            data['data'] = "fetched"
        else:
            data['data'] = None

    
    return JsonResponse(data, safe=False)



def upload_product(request):
    name = request.GET.get('name', '')
    discount = request.GET.get('discount', '')
    user_id = request.GET.get('user_id', '')
    price = request.GET.get('price', '')
    distance_price = request.GET.get('distance_price', '')
    image = request.GET.get('image', '')
    category_id = request.GET.get('category_id', '')
    
    data = {
        "status": True,
        "message": "success",
        "data": "error",
    }


    if name and discount and user_id and price and category_id and image:

        product_id = random.unique_id()
        
        product = AAAProducts.objects.create(
            user_id = user_id,
            name = name,
            price = price,
            product_id = product_id,
            category_id = category_id,
            status = "approved",
            time = timezone.now(),
        )

        ima = AAAproductImages.objects.create(
            product_id = product_id,
            image = image,
            image_id = random.unique_id(),
            status = "approved",
            time = timezone.now(),

        )
        
        data.update({"data": "inserted"})

    else:    
        data.update({"data": "All are required fields"})
    
    return JsonResponse(data, safe=False)

def check_name(request):
    name = request.GET.get('check_name', '')

    data = {
        "status": True,
        "message": "success",
        "data": "empty"
    }
    if name:
        product = ProductCategory.objects.filter(status="approved", name=name).first()

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
    image = request.FILES.get('image', '')
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if name and discount and price  and product_id:
        
        product =  AAAProducts.objects.filter(product_id=product_id).first()

        if product:
            
            product.name = name
            product.discount = discount
            product.price = price
            # product.distance_price = 
            product.save(using='aaaaa')

            data.update({
                "products": {
                    "name": product.name,
                    "discount": product.discount,
                    "price": product.price,
                }
            })
            return JsonResponse(data, safe=False)
    
        data.update({"data": "product is not available"})
        return JsonResponse(data, safe=False)



    data.update({"data": "All fields are required"})
    return JsonResponse(data, safe=False)


# signin system

def create_account(request):
    fullname = request.GET.get('firstname', '')
    lastname = request.GET.get('lastname', '')
    email = request.GET.get('email', '')
    phone = request.GET.get('phone', '')

    data = {
        "status": True,
        "message": "success",
    }

    if email:
        ex = AAAUsers.objects.filter(email=email, status="approved").first()

        if not ex:    
            if fullname and lastname and phone:
                user_id = random.unique_id()

                otp = random.randint(100000, 999999)

                send_mail(
                    "Your OTP Code",
                    f"Your OTP is {otp}. Do not share it with anyone.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )

                user = AAAUsers.objects.create(
                    firstname = firstname,
                    lastname = lastname,
                    email = email,
                    password = "",
                    profile = "",
                    city = "city",
                    state = "state",
                    district = "district",
                    phone = phone,
                    user_type = 'user',
                    user_id = user_id,
                    status="disapproved",
                    time=timezone.now(),
                )

                data.update({"signin": user_id, "otp": otp})
            else:
                data.update({"signin": "empty"})
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

        passw = AAAUsers.objects.filter(user_id=user_id).first()

        if passw:
            passw.password = password
            passw.status="approved"
            passw.save()

            data.update({"signin": passw.user_id})

        else:
            data.update({"signin": "no"})
    else:
        data.update({"signin": "empty"})
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
    address = requesrt.GET.get('address', '')
    user_id =  request.GET.get('user_id', '')
    
    data = {
        "status": True,
        "message": "success",
    }

    if address and user_id:
        
        ex = AAAUsers.objects.filter(user_id=user_id).first()

        if ex:

            pass

        data.update({"signin": "no"})

    else:
        data.update({"signin": "empty"})
    return JsonResponse(data, safe=False)

# end signin system 


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
                })
        
        else:
            data['profile'].append({"action": "no"})

    else:
        data['profile'].append({"action": "empty"})
    return JsonResponse(data, safe=False)

@method_decorator(csrf_exempt, name='dispatch')
class CategoryUpload(View):

    def get(self, request):
        name = request.GET.get('name', '')
        image = request.GET.get('image')

        data = {
            "status": True,
            "message": "success",
        }

        if name and image:
            ex = ProductCategory.objects.filter(
                status="approved",
                name=name
            ).first()

            if not ex:
                ProductCategory.objects.create(
                    name=name,
                    status="approved",
                    img=image,
                    category_id=random.unique_id(),
                    time=timezone.now(),
                )
                data["data"] = "inserted"
            else:
                data["data"] = "exists"
        else:
            data["status"] = False
            data["message"] = "name and image required"

        return JsonResponse(data)

class Category(View):
    def get(self, request):
        products = ProductCategory.objects.using("aaaaa").filter(status="approved")
        data = {
            "status": True,
            "message": "success",
            "category": list(products.values())
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
        cat = AAAProductsjects.filter(category_id=cat_id)
        if cat:
            data['category'] = list(cat.values())
        else:

            data['category'].append({"action": "no"})
    else:
        
        data['category'].append({"action": "empty"})

    return JsonResponse(data, safe=False)

def search(request):
    search = request.GET.get('search', '')

    data = {
        "status": True,
        "message": "success",
        "search": []
    }

    if search:
        product = AAAProductsjects.filter(status="approved", name__contains=search)
        
        if product:
            data['search'] = list(product.values())
        else:
            data['search'].append({"action": "no"})

    else:
        data['search'].append({"action": "empty"})

    return JsonResponse(data, safe=False)





def edit_profile(request):
    fullname = request.GET.get('fullname', '')
    lastname = request.GET.get('lastname', '')
    email = request.GET.get('email', '')
    phone = request.GET.get('phone', '')
    address = request.GET.get('address' '')
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    pincode = request.GET.get('pincode', '')
    district = request.GET.get('district', '')
    user_id = request.GET.get('user_id', '')


    data = {
        "status": True,
        "message": "success",
    }

    if fullname and lastname and email and phone and address and city and state and district and pincode and user_id:
        
        user = FreshUsers.objects.filter(user_id=user_id, status="approved").first()

        if user:

            user.fullname = fullname
            user.lastname = lastname
            user.email = email
            user.phone = phone
            user.address = address
            user.city = city
            user.state = state
            user.pincode = pincode
            user.district = district

            user.save()
        
            data.update({"data": "completed"})
            return JsonResponse(data, safe=False)
        else:

            data.update({"data": "user is not available"})
            return JsonResponse(data, safe=False)
    else:    
        data.update({"data": "empty"})
        return JsonResponse(data, safe=False)



def delete_product(request):
    product_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }
    if product_id:
        product = FreshAAAProductsjects.filter(product_id = product_id).first()

        if product:
            product.status = "delete"
            product.save()

        data.update({"data": "deleted"})
        return JsonResponse(data, safe=False)
    else: 
        data.update({"data": "email fiels is empty"})
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
                    "image": image
                }


                data["order"].append(item)
        else:
            data['order'].append({"action": "db_empty"})

    else:
        data['order'].append({"action": "empty"})

    return JsonResponse(data, safe=False)


def delete_order(request):
    product_id = request.GET.get('product_id', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "order": []
    }

    if product_id:
        order = Orders.objects.filter(product_id=product_id, status="approved").first()

        if order:
            order.delete()
        item = {"action": "deleted"}
        data['order'].append(item)

    else:        
        item = {"action": "empty"}
        data['order'].append(item)

       
    return JsonResponse(data, safe=False)
    
# end cart



def change_image(request):
    image = request.FILES.get('image', '')
    prodcut_id = request.GET.get('product_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if image and product_id:
        im = FreshAAAProductsjects.filter(user=product_id).first()
      
        if im:
                        
            data.update({"data": "updated"})
            return JsonResponse(data, safe=False)

        else:
                        
            data.update({"data": "deleted"})
            return JsonResponse(data, safe=False)

    else:    
        data.update({"data": "empty"})
        return JsonResponse(data, safe=False)







