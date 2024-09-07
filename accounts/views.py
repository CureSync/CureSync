from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.models import User, auth
from main_app.models import patient, doctor
from datetime import datetime
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from cloudinary import uploader
from cloudinary.utils import cloudinary_url

from django.core.mail import send_mail
import random
import string
from django.conf import settings

def logout(request):
    auth.logout(request)
    request.session.pop('patientid', None)
    request.session.pop('doctorid', None)
    request.session.pop('adminid', None)
    return render(request, 'homepage/index.html')

def sign_in_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            try:
                if user.is_superuser:
                    auth.login(request, user)
                    return redirect('admin_ui')
            except:
                messages.info(request, 'Please enter the correct username and password for an admin account.')
                return redirect('sign_in_admin')
        else:
            messages.info(request, 'Please enter the correct username and password for an admin account.')
            return redirect('sign_in_admin')
    else:
        return render(request, 'admin/signin/signin.html')

def signup_patient(request):
    if request.method == 'POST':
        form_data = {
            'username': request.POST.get('username'),
            'email': request.POST.get('email'),
            'name': request.POST.get('name'),
            'dob': request.POST.get('dob'),
            'gender': request.POST.get('gender'),
            'address': request.POST.get('address'),
            'mobile': request.POST.get('mobile'),
            'password': request.POST.get('password'),
            'password1': request.POST.get('password1'),
        }

        DEFAULT_IMAGE_URL = "https://res.cloudinary.com/dj0ibhe7o/image/upload/v1725732817/CureSync/a3nnedse2frsntlkcojx.webp"
    
        if 'profile_picture' in request.FILES:
            image_file = request.FILES['profile_picture']
            try:
                upload_result = uploader.upload(image_file.read(), 
                                                folder="profile_pictures", 
                                                public_id=f"user_{form_data['username']}")  
                image_url = upload_result['secure_url']
                form_data['profile_picture'] = image_url
            except Exception as e:
                print(f"Cloudinary upload failed: {str(e)}")
                form_data['profile_picture'] = DEFAULT_IMAGE_URL
        else:
            form_data['profile_picture'] = DEFAULT_IMAGE_URL
        
            

        # Validate form data
        if not all(form_data.values()):
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'patient/signup_form/signup.html', {'form_data': form_data})

        if form_data['password'] != form_data['password1']:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'patient/signup_form/signup.html', {'form_data': form_data})

        if User.objects.filter(username=form_data['username']).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'patient/signup_form/signup.html', {'form_data': form_data})

        if User.objects.filter(email=form_data['email']).exists():
            messages.error(request, 'Email already taken.')
            return render(request, 'patient/signup_form/signup.html', {'form_data': form_data})

        # Generate and send OTP
        otp = generate_otp()
        send_otp_email(form_data['email'], otp)

        # Store form data and OTP in session
        request.session['patient_signup_data'] = form_data
        request.session['patient_signup_otp'] = otp
        request.session.set_expiry(600)  # OTP expires in 10 minutes

        return redirect('verify_otp_patient')

    return render(request, 'patient/signup_form/signup.html')

def verify_otp_patient(request):
    form_data = request.session.get('patient_signup_data')
    if not form_data:
        messages.error(request, 'Session expired. Please fill the form again.')
        return redirect('signup_patient')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('patient_signup_otp')

        if entered_otp == stored_otp:
            # Create user and patient records
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=form_data['password']
            )
            patient_new = patient(
                user=user,
                name=form_data['name'],
                dob=form_data['dob'],
                gender=form_data['gender'],
                address=form_data['address'],
                mobile_no=form_data['mobile'],
                profile_picture=form_data['profile_picture']
            )
            patient_new.save()

            # Clear session data
            del request.session['patient_signup_data']
            del request.session['patient_signup_otp']

            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('sign_in_patient')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'patient/signup_form/verify_otp.html')

def sign_in_patient(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            try:
                if user.patient.is_patient:
                    auth.login(request, user)
                    request.session['patientusername'] = user.username
                    return redirect('patient_ui')
            except:
                messages.info(request, 'Invalid credentials')
                return redirect('sign_in_patient')
        else:
            messages.info(request, 'Invalid credentials')
            return redirect('sign_in_patient')
    else:
        return render(request, 'patient/signin_page/index.html')

def savepdata(request, patientusername):
    if request.method == 'POST':
        name = request.POST.get('name')
        dob = request.POST.get('dob')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        mobile_no = request.POST.get('mobile_no')
        profile_picture = request.POST.get('profile_picture')
        
        try:
            dobdate = datetime.strptime(dob, '%Y-%m-%d')
            puser = User.objects.get(username=patientusername)
            patient.objects.filter(pk=puser.patient).update(
                name=name, 
                dob=dobdate, 
                gender=gender, 
                address=address, 
                mobile_no=mobile_no
            )

            # Handle image upload
            if 'profile_picture' in request.FILES:
                image_url=""
                if 'profile_picture' in request.FILES:
                    image_file = request.FILES['profile_picture']
                    try:
                        upload_result = uploader.upload(image_file.read(), 
                                                        folder="profile_pictures", 
                                                        public_id=f"user_{patientusername}")  
                        image_url = upload_result['secure_url']
                    except Exception as e:
                        print(f"Cloudinary upload failed: {str(e)}")

                if image_url != puser.patient.profile_picture and image_url != "":
                    patient.objects.filter(pk=puser.patient).update(profile_picture=image_url)

            messages.success(request, "Changes saved successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return redirect('pviewprofile', patientusername)
    
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    subject = 'Your OTP for Doctor Signup'
    message = f'Your OTP is: {otp}. This OTP will expire in 10 minutes.'
    from_email = 'your-email@example.com'
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list)

def signup_doctor(request):
    if request.method == 'POST':
        form_data = {
            'username': request.POST.get('username'),
            'email': request.POST.get('email'),
            'name': request.POST.get('name'),
            'dob': request.POST.get('dob'),
            'gender': request.POST.get('gender'),
            'address': request.POST.get('address'),
            'mobile': request.POST.get('mobile'),
            'password': request.POST.get('password'),
            'password1': request.POST.get('password1'),
            'registration_no': request.POST.get('registration_no'),
            'year_of_registration': request.POST.get('year_of_registration'),
            'qualification': request.POST.get('qualification'),
            'State_Medical_Council': request.POST.get('State_Medical_Council'),
            'specialization': request.POST.get('specialization'),
        }

        DEFAULT_IMAGE_URL = "https://res.cloudinary.com/dj0ibhe7o/image/upload/v1725732817/CureSync/a3nnedse2frsntlkcojx.webp"
    
        if 'profile_picture' in request.FILES:
            image_file = request.FILES['profile_picture']
            try:
                upload_result = uploader.upload(image_file.read(), 
                                                folder="profile_pictures",  
                                                public_id=f"user_{form_data['username']}") 
                image_url = upload_result['secure_url']
                form_data['profile_picture'] = image_url
            except Exception as e:
                print(f"Cloudinary upload failed: {str(e)}")
                form_data['profile_picture'] = DEFAULT_IMAGE_URL
        else:
            form_data['profile_picture'] = DEFAULT_IMAGE_URL
    
        # Validate form data
        if not all(form_data.values()):
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'doctor/signup_form/signup.html', {'form_data': form_data})

        if form_data['password'] != form_data['password1']:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'doctor/signup_form/signup.html', {'form_data': form_data})

        if User.objects.filter(username=form_data['username']).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'doctor/signup_form/signup.html', {'form_data': form_data})

        if User.objects.filter(email=form_data['email']).exists():
            messages.error(request, 'Email already taken.')
            return render(request, 'doctor/signup_form/signup.html', {'form_data': form_data})

        # Generate and send OTP
        otp = generate_otp()
        send_otp_email(form_data['email'], otp)

        # Store form data and OTP in session
        request.session['doctor_signup_data'] = form_data
        request.session['doctor_signup_otp'] = otp
        request.session.set_expiry(600)  # OTP expires in 10 minutes

        return redirect('verify_otp')

    return render(request, 'doctor/signup_form/signup.html')

def verify_otp(request):
    form_data = request.session.get('doctor_signup_data')
    if not form_data:
        messages.error(request, 'Session expired. Please fill the form again.')
        return redirect('signup_doctor')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('doctor_signup_otp')

        if entered_otp == stored_otp:
            # Create user and doctor records
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=form_data['password']
            )
            doctor_new = doctor(
                user=user,
                name=form_data['name'],
                dob=form_data['dob'],
                gender=form_data['gender'],
                address=form_data['address'],
                mobile_no=form_data['mobile'],
                registration_no=form_data['registration_no'],
                year_of_registration=form_data['year_of_registration'],
                qualification=form_data['qualification'],
                State_Medical_Council=form_data['State_Medical_Council'],
                specialization=form_data['specialization'],
                profile_picture=form_data['profile_picture']
            )
            doctor_new.save()

            # Clear session data
            del request.session['doctor_signup_data']
            del request.session['doctor_signup_otp']

            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('sign_in_doctor')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'doctor/verify_otp.html')

def sign_in_doctor(request):
    if request.method == 'GET':
        return render(request, 'doctor/signin_page/index.html')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            try:
                if user.doctor.is_doctor:
                    auth.login(request, user)
                    request.session['doctorusername'] = user.username
                    return redirect('doctor_ui')
            except:
                messages.info(request, 'Invalid credentials')
                return redirect('sign_in_doctor')
        else:
            messages.info(request, 'Invalid credentials')
            return redirect('sign_in_doctor')
    else:
        return render(request, 'doctor/signin_page/index.html')

def saveddata(request, doctorusername):
    if request.method == 'POST':
        try:
            name = request.POST['name']
            dob = request.POST['dob']
            gender = request.POST['gender']
            address = request.POST['address']
            mobile_no = request.POST['mobile_no']
            registration_no = request.POST['registration_no']
            year_of_registration = request.POST['year_of_registration']
            qualification = request.POST['qualification']
            State_Medical_Council = request.POST['State_Medical_Council']
            specialization = request.POST['specialization']
            dobdate = datetime.strptime(dob, '%Y-%m-%d')
            yor = datetime.strptime(year_of_registration, '%Y-%m-%d')

            duser = User.objects.get(username=doctorusername)

            doctor.objects.filter(pk=duser.doctor).update(name=name, dob=dob, gender=gender, address=address, mobile_no=mobile_no, registration_no=registration_no, year_of_registration=yor, qualification=qualification, State_Medical_Council=State_Medical_Council, specialization=specialization)

            # Handle image upload
            if 'profile_picture' in request.FILES:
            
                if 'profile_picture' in request.FILES:
                    image_url=""
                    if 'profile_picture' in request.FILES:
                        image_file = request.FILES['profile_picture']
                        try:
                            upload_result = uploader.upload(image_file.read(), 
                                                            folder="profile_pictures", 
                                                            public_id=f"user_{doctorusername}")  
                            image_url = upload_result['secure_url']
                        except Exception as e:
                            print(f"Cloudinary upload failed: {str(e)}")


                if image_url != duser.doctor.profile_picture and image_url != "":
                    doctor.objects.filter(pk=duser.doctor).update(profile_picture=image_url)
                    messages.success(request, "Changes saved successfully!")
        except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        return redirect('dviewprofile', doctorusername)
