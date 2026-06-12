from django.shortcuts import render
from django.http import JsonResponse
from .models import *
from django.views import View
from shared_lib.utils import insertions, random
from django.utils import timezone

# Create your views here.

def home(request):
    products = KrishiProducts.objects.filter(status="approved")
    data = {
        "status": True,
        "message": "success",
        "products": list(products.values()),
    }
    return JsonResponse(data, safe=False)


class SignIn(View):
    def get(self, request):
        email = request.GET.get('email', '')
        password = request.GET.get('password', '')


        if email and password:
            pass
        
        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)
    

class SignUp(View):
       def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)


# farmer user

class Products(View):
    def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)

class Orders(View):
       def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)


class Profile(View):
       def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)


class Home(View):
       def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)



# admin user

class EditProduct(View):
   def get(self, request):

        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)

class UploadProduct(View):
    def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

        return JsonResponse(data, safe=False)


class DeleteProduct(View):
    def get(self, request):


        data = {
            "status": True,
            "message": "success"
        }

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


def confirm(request):
    user_id = request.GET.get('user_id', '')
    address_id = request.GET.get('address_id', '')
    order_id = request.GET.get('order_id', '')


    data = {
        "status": True,
        "message": "success",
        "order": []
        
    }
    if user_id:
        
        order = Orders.objects.filter(status="approved", user_id=user_id)
        order.status = "confirmed"
        order.save()

    
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
    


# cart end