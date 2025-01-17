from datetime import datetime,date
from django.shortcuts import render, redirect
import openpyxl
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login
from .forms import  DailyActivityReportForm
from .models import DailyActivityReport, CustomUser , Department
from django.contrib.auth.decorators import login_required , user_passes_test
from  django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
import random
from django.conf import settings
from django.contrib.auth import get_user_model  
from django.core.exceptions import ObjectDoesNotExist



def home(request):
    return render(request, 'users/login.html')

def create_user(request):
    return render(request, 'users/create_user.html' )

# Login Page 
def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
       
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"Authenticated user: {user.username}")
            auth_login(request, user)
            
           
            if user.is_superuser:
                print("User is superuser (admin)")
                return redirect('users:admin_dashboard')  
            else:
                print("User is not admin")
                return redirect('users:daily_activity') 
        else:
            print("Authentication failed.")
            messages.error(request, "Invalid username or password!")
            return render(request, 'users/login.html')

    return render(request, 'users/login.html')

# Admin Dashboard (Add User/Admin page)
@login_required
def admin_dashboard(request):
    action = request.GET.get('action')
    departments = Department.objects.all()

    if request.method == 'POST':
        # Get the form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        department_name = request.POST.get('department')

        # Check if the department exists
        try:
            department = Department.objects.get(name=department_name)
        except Department.DoesNotExist:
            return render(request, 'users/admin_dashboard.html', {
                'action': action,
                'departments': departments,
                'error': f"Department {department_name} does not exist!"
            })

        # Check if the username already exists
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'users/admin_dashboard.html', {
                'action': action,
                'departments': departments,
                'error': f"Username {username} already exists!"
            })

        # Create the user based on the action
        if action == 'add_user':
            user = CustomUser.objects.create_user(username=username, password=password)
            user.save()
            

        elif action == 'add_admin':
            user = CustomUser.objects.create_user(username=username, password=password)
            user.is_staff = True
            user.is_superuser = True
            user.save()

            permissions = request.POST.getlist('permissions')
            if 'can_edit' in permissions:
                user.can_edit = True
            if 'can_delete' in permissions:
                user.can_delete = True
            if 'can_add_admin' in permissions:
                user.can_add_admin = True
            user.save()

        # Redirect to the same page after the operation
        return redirect('users:admin_dashboard')

    return render(request, 'users/admin_dashboard.html', {
        'action': action,
        'departments': departments
    })
   
# User Daily Activity Page
@login_required
def daily_activity(request):
    user = request.user
    today = date.today()

    # If the user doesn't have a daily activity report yet, create one
    try:
        daily_report = DailyActivityReport.objects.get(user=user, date=date.today())
    except DailyActivityReport.DoesNotExist:
        daily_report = None

    if request.method == 'POST':
        form = DailyActivityReportForm(request.POST, instance=daily_report)

        if form.is_valid():
            activity_report = form.save(commit=False)
            activity_report.user = user
            activity_report.save()
            messages.success(request, "Your daily activity report has been updated.")
            return redirect('users:daily_activity')
    else:
        form = DailyActivityReportForm(instance=daily_report)

    return render(request, 'users/daily_activity.html', {'form': form})

# Forgot password request page
def forgot_password(request):
    if request.method == 'POST':
        # Get the username or email submitted by the user
        username_or_email = request.POST.get('username_or_email')

        # Get the custom user model
        CustomUser = get_user_model()

        # Try to fetch the user by username or email
        try:
            user = CustomUser.objects.get(username=username_or_email)
        except ObjectDoesNotExist:
            try:
                user = CustomUser.objects.get(email=username_or_email)
            except ObjectDoesNotExist:
                messages.error(request, "User with this username or email does not exist.")
                return redirect('users:forgot_password')

        verification_code = random.randint(100000, 999999)

        admin_email = 'newsletter@print3.com'  
        subject = f"Password Reset Request for {user.username}"
        message = f"""
        A password reset request has been made for the user {user.username}.
        Username: {user.username}
        Department: {user.department.name if user.department else "No department"}
        Verification Code: {verification_code}
        """

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['newsletter@print3.in'])

        request.session['verification_code'] = verification_code
        request.session['user_id'] = user.id

        messages.success(request, "A password reset request has been sent to the admin.")
        return redirect('users:forgot_password')  

    return render(request, 'users/forgot_password.html')


# Admin view to verify the password reset request and reset the password
@login_required
def verify_and_reset_password(request):
    if request.method == 'POST':
        verification_code = request.POST.get('verification_code')
        new_password = request.POST.get('new_password')

        # Check if the verification code matches
        if str(verification_code) == str(request.session.get('verification_code')):
            # Get the user and reset password
            user_id = request.session.get('user_id')
            user = User.objects.get(id=user_id)

            # Set the new password
            user.set_password(new_password)
            user.save()

            # Send confirmation email to the user
            send_mail(
                'Your password has been reset',
                f'Your password has been successfully reset by the admin.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )

            messages.success(request, f"Password has been reset for {user.username}")
            return redirect('users:admin_dashboard')
        else:
            messages.error(request, "Invalid verification code.")
            return redirect('users:admin_dashboard')

    return render(request, 'users/verify_password_reset.html')

