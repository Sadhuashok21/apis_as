from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from shared_lib.utils import insertions, random
from shared_lib.sfs_core.models import AllUsers
from django.core.mail import send_mail
from django.db.models import Q
from django.contrib.auth.hashers import check_password


version = "1.0"

sfs_app_version = "2.1"

data = {
    "status" : True,
    "message": "success"
}   

def index(request):
    
    #return redirect("https://www.ascentracoresolutions.com")
    return HttpResponse("You don't have access to this page. Please contact support for more information.")

def insert_sfs_app(request):

    activity_id = request.GET.get("activity_id", "")


    if activity_id:

        insertions.insert_activity(random.get_client_ip(request), sfs_app_version, activity_id, request.GET.get('user_id', 'anonymous'))
        return JsonResponse(data, safe=False)
    else:

        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

def error_sfs_app(request):
    activity_id = request.GET.get("activity_id", "")
    msg = request.GET.get('msg', '')

    if activity_id and msg:

        insertions.insert_error(random.get_client_ip(request), request.GET.get('user_id', 'anonymous'), sfs_app_version, msg, activity_id)
        return JsonResponse(data, safe=False)
    
    else:
        
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)


def email_i(request):
    email = request.GET.get('email', '')

    user_id = request.GET.get('user_id', '')

    if email and user_id:
        
        insertions.insert_email(random.get_client_ip(request), user_id, sfs_app_version, email)
        return JsonResponse(data, safe=False)
    else:
        
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

def check_signin(request):
    email = request.GET.get('email', '')

    if email:
        user = AllUsers.objects.filter(email=email).first()

        if user is None:
            return JsonResponse({"status": False, "message": "User not found", "signin": "no"}, safe=False)
    
        return JsonResponse({
            "status": True,
            "message": "Login successful",
            "signin": "success",
            "user_id": user.user_id
        })


    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

def signup(request):
    name = request.GET.get('name', '')
    lastname = request.GET.get('lastname', '')
    username = request.GET.get('username', '')
    password = request.GET.get('password', '')
    email = request.GET.get('email', '')
    platform = request.GET.get('platform', '')
    platform_name = request.GET.get('platform_name', '')
    type = request.GET.get('type', '')
    photo = request.GET.get('photo', '')

    if name and lastname and platform and platform_name and username and password and email and type:

        user_exists = AllUsers.objects.filter(username=username).first()

        if user_exists:
            print(user_exists.user_id)
            return JsonResponse({"status": False, "message": "Username", "signin": user_exists.user_id}, safe=False)


        user_id = random.unique_id()
        user = AllUsers(
            name=name,
            lastname=lastname, 
            email=email,
            user_id=user_id, 
            username=username,
            platform=platform,
            platform_name=platform_name,
            type = type,
            profile = photo if photo else None
        )

        print(type, platform, platform_name, username, password, email)

        user.set_password(password)
        
        user.save()

        data.update({"message": "success", "signin": "new", "user_id": user_id})

        # insertions.insert_name(random.get_client_ip(request), sfs_app_version, name)
        return JsonResponse(data, safe=False)


    else:
        data.update({"message": "failed", "signin": "no"})
        return JsonResponse(data, safe=False)


def check_username(request):
    username = request.GET.get('username', '')

    if username:
        user_exists = AllUsers.objects.filter(username=username).exists()
        if user_exists:
            return JsonResponse({"status": True, "message": "Username already exists", "signin": "exists"}, safe=False)
        else:
            return JsonResponse({"status": True, "message": "Username available", "signin": "available"}, safe=False)
    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

def signin(request):
    username = request.GET.get('username', '')
    password = request.GET.get('password', '')

    if username and password:
        user = AllUsers.objects.filter(Q(username=username) | Q(email=username)).first()

        if user is None:
            return JsonResponse({"status": False, "message": "User not found", "signin": "no"}, safe=False)
    
        if check_password(password, user.password):

            return JsonResponse({
                "status": True,
                "message": "Login successful",
                "signin": "success",
                "user_id": user.user_id
            })

        return JsonResponse({
            "status": False,
            "message": "Invalid password",
            "signin": "no"
        })

    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

def forgot_password_i(request):
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id', '')

    if email and user_id:
        
        insertions.insert_forgot_password(random.get_client_ip(request), user_id, sfs_app_version, email)
        return JsonResponse(data, safe=False)

    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)


def check_mail(request):
    email = request.GET.get('email', '')

    if email:
        user_exists = AllUsers.objects.filter(email=email).exists()
        if user_exists:
            return JsonResponse({"status": True, "message": "Email exists", "signin": "exists"}, safe=False)
        
        otp = random.generate_otp()

        from django.core.mail import EmailMultiAlternatives

        # Your generated OTP
        subject = "Your OTP for Ascentracore Solutions"
        from_email = "noreply@ascentracoresolutions.com"
        to = [email]

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <title>OTP Verification</title>
        </head>

        <body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:30px 0;">
        <tr>
        <td align="center">

        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:15px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,.1);">

        <tr>
        <td align="center" style="background:#1565C0;padding:30px;">
            <h1 style="color:white;margin:0;font-size:30px;">
                Ascentracore Solutions
            </h1>

            <p style="color:#dfefff;margin-top:8px;font-size:16px;">
                Secure Email Verification
            </p>
        </td>
        </tr>

        <tr>
        <td style="padding:40px;">

        <h2 style="margin-top:0;color:#333;">
        Hello,
        </h2>

        <p style="font-size:16px;color:#555;line-height:28px;">
        Thank you for using <strong>Ascentracore Solutions</strong>.
        Use the One-Time Password (OTP) below to verify your email address.
        </p>

        <div style="margin:35px 0;text-align:center;">

        <div style="
        display:inline-block;
        background:#1565C0;
        color:white;
        font-size:36px;
        font-weight:bold;
        letter-spacing:8px;
        padding:18px 45px;
        border-radius:12px;
        ">
        {otp}
        </div>

        </div>

        <p style="font-size:15px;color:#666;line-height:26px;">
        This OTP is valid for
        <b>5 minutes</b>.
        Please do not share this code with anyone.
        </p>

        <div style="margin-top:35px;padding:18px;background:#FFF8E1;border-left:5px solid #FFC107;border-radius:8px;">

        <strong>Security Tip</strong><br>
        If you didn't request this verification code, you can safely ignore this email.

        </div>

        </td>
        </tr>

        <tr>
        <td align="center" style="padding:25px;background:#f7f7f7;">

        <p style="margin:0;color:#666;font-size:14px;">
        © 2026 Ascentracore Solutions. All Rights Reserved.
        </p>

        <p style="margin-top:8px;font-size:13px;">
        <a href="https://www.ascentracoresolutions.com" style="color:#1565C0;text-decoration:none;">
        www.ascentracoresolutions.com
        </a>
        </p>

        </td>
        </tr>

        </table>

        </td>
        </tr>
        </table>

        </body>
        </html>
        """
        text_content = f"Your OTP is {otp}"

        msg = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            to
        )

        msg.attach_alternative(html_content, "text/html")
        msg.send()


        data.update({"otp": otp, "signin": "otp_sent"})
        return JsonResponse(data, safe=False)

    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)


def otp_i(request):

    email = request.GET.get('email', '')
    if email:
        otp = random.generate_otp()

        from django.core.mail import EmailMultiAlternatives

        # Your generated OTP
        subject = "Your OTP for Ascentracore Solutions"
        from_email = "noreply@ascentracoresolutions.com"
        to = [email]

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <title>OTP Verification</title>
        </head>

        <body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:30px 0;">
        <tr>
        <td align="center">

        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:15px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,.1);">

        <tr>
        <td align="center" style="background:#1565C0;padding:30px;">
            <h1 style="color:white;margin:0;font-size:30px;">
                Ascentracore Solutions
            </h1>

            <p style="color:#dfefff;margin-top:8px;font-size:16px;">
                Secure Email Verification
            </p>
        </td>
        </tr>

        <tr>
        <td style="padding:40px;">

        <h2 style="margin-top:0;color:#333;">
        Hello,
        </h2>

        <p style="font-size:16px;color:#555;line-height:28px;">
        Thank you for using <strong>Ascentracore Solutions</strong>.
        Use the One-Time Password (OTP) below to verify your email address.
        </p>

        <div style="margin:35px 0;text-align:center;">

        <div style="
        display:inline-block;
        background:#1565C0;
        color:white;
        font-size:36px;
        font-weight:bold;
        letter-spacing:8px;
        padding:18px 45px;
        border-radius:12px;
        ">
        {otp}
        </div>

        </div>

        <p style="font-size:15px;color:#666;line-height:26px;">
        This OTP is valid for
        <b>5 minutes</b>.
        Please do not share this code with anyone.
        </p>

        <div style="margin-top:35px;padding:18px;background:#FFF8E1;border-left:5px solid #FFC107;border-radius:8px;">

        <strong>Security Tip</strong><br>
        If you didn't request this verification code, you can safely ignore this email.

        </div>

        </td>
        </tr>

        <tr>
        <td align="center" style="padding:25px;background:#f7f7f7;">

        <p style="margin:0;color:#666;font-size:14px;">
        © 2026 Ascentracore Solutions. All Rights Reserved.
        </p>

        <p style="margin-top:8px;font-size:13px;">
        <a href="https://www.ascentracoresolutions.com" style="color:#1565C0;text-decoration:none;">
        www.ascentracoresolutions.com
        </a>
        </p>

        </td>
        </tr>

        </table>

        </td>
        </tr>
        </table>

        </body>
        </html>
        """
        text_content = f"Your OTP is {otp}"

        msg = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            to
        )

        msg.attach_alternative(html_content, "text/html")
        msg.send()


        data.update({"otp": otp, "signin": "otp_sent"})
        return JsonResponse(data, safe=False)

    else:
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)





def er_400(request, exception):
    try:
        error_msg = f"400 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 400, "website", "sfs" )     


    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "400.html", status=400)



def er_401(request, exception):
    try:
        error_msg = f"401 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 401, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 401, "website", "sfs" )     




        insertions.insert_error(random.get_client_ip(request), request.session.get('user_id', 'anonymous'), version, error_msg, request.path)
        
    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "401.html", status=401)


def er_403(request, exception):
    try:
        error_msg = f"403 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 403, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 403, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "403.html", status=403)


def er_404(request, exception):

    try:
        error_msg = f"404 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 404, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 404, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "404.html", {"path": request.path}, status=404)



def er_408(request, exception):
    try:
        error_msg = f"408 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 408, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 408, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "408.html", status=408)


def er_500(request):
    try:
        error_msg = f"500 at {request.path}"

        if request.user.is_authenticated:
                
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 500, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 500, "website", "sfs" )     
    
    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "500.html", {"path": request.path}, status=500)


def er_502(request, exception):
    try:
        error_msg = f"502 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 502, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 502, "website", "sfs" )     


    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "502.html", status=502)


def er_503(request, exception):
    try:
        error_msg = f"503 at {request.path}"


        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 503, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 503, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "503.html", status=503)


def er_504(request, exception):
    try:
        error_msg = f"504 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 504, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 504, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "504.html", status=504)


def er_505(request, exception):
    try:
        error_msg = f"505 at {request.path}"

        if request.user.is_authenticated:
            
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 505, "website", "sfs", request.user.user_id)
        else:
            insertions.insert_error(random.get_client_ip(request), version, error_msg, request.build_absolute_uri(), 505, "website", "sfs" )     

    except Exception as e:
        # Log to console or ignore — don’t break the 404 page
        print("Failed to log 404:", e)

    return render(request, "505.html", status=505)







