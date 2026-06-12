from django.shortcuts import render
from aaaab.models import *
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

# Create your views here.
def orders(request):
    user_id = request.GET.get('user_id', '')

    data = {
        'status': True,
        'message': 'success',
        'orders': []
    }

    if user_id:
        orders = Orders.objects.filter(status="confirmed", user_id=user_id)

        if orders.exists():

            data.update({"orders": list(orders)})
        else:
            data['orders'].append({"action": "db_empty"})
        
    else:
        data['orders'].append({"action": "empty"})
    return JsonResponse(data, safe=False)

def completed(request):

    user_id = request.GET.get('user_id', '')

    data = {
        'status': True,
        'message': 'success',
        'orders': []
    }

    if user_id:
        orders = Orders.objects.filter(status="completed", user_id=user_id)

        data.update({"orders": list(orders.values())})
    else:
        data['orders'].append({"action": "empty"})
    return JsonResponse(data, safe=False)


def all_orders(request):
    orders = Orders.objects.filter(status="confirmed")

    data = {
        'status': True,
        'message': 'success',
        'orders': []
    }
    if orders:
        data['orders'] = list(orders.values())
        
    else:
        data['orders'].append({'action': 'db_empty'})
    return JsonResponse(data, safe=False)



def o_complete(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
        'status': True,
        'message': 'success',
    }
    if user_id:
        orders = Orders.objects.filter(status="confirmed", user_id=user_id)

        if orders:
            for order in orders:
                order.status = "completed"
                order.save()
                data.update({"action": "complete"})
        else:
            data.update({"action": "db_empty"})
    else:
        data.update({"action": "empty"})
        
    return JsonResponse(data, safe=False)



def profile(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
        'status': True,
        'message': 'success',
    }
    if user_id:
        user = Users.objects.filter(user_id=user_id).first()

        if user:
            
            data.update({
                "name": user.firstname,
                "email": user.email,
                "phone": user.phone,

                })

        else:
            data.update({"action": "no"})

    else:
        data.update({"action": "empty"})
        
    return JsonResponse(data, safe=False)


def view(request):
    pass



