from audioop import avg
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from datetime import date
from django.db.models import Avg

from django.contrib import messages
from django.contrib.auth.models import User , auth
from .models import patient , doctor , diseaseinfo , consultation ,rating_review
from chats.models import Chat,Feedback

import joblib as jb
model = jb.load('trained_model')

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
import logging
import os
from django.templatetags.static import static
from django.http import JsonResponse

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO



logger = logging.getLogger(__name__)
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def download_pdf(request):
    # Example data; replace with actual data from your context
    context = {
        'disease': request.GET.get('disease', 'Unknown Disease'),
        'confidence': request.GET.get('confidence', '0'),
        'consultdoctor': request.GET.get('consultdoctor', 'General'),
    }
    pdf = render_to_pdf('pdf_template.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Report_{context['disease']}.pdf"
        content = f"inline; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse("Error generating PDF", status=400)

def home(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            # Check if the user is a patient
            patientusername = request.session.get('patientusername')
            if patientusername:
                try:
                    puser = User.objects.get(username=patientusername)
                    logger.info(f"Redirecting patient user: {patientusername}")
                    return redirect('patient_ui')  # Redirects to the patient_ui view
                except User.DoesNotExist:
                    logger.error(f"Patient user does not exist: {patientusername}")

            # Check if the user is a doctor
            doctorusername = request.session.get('doctorusername')
            if doctorusername:
                try:
                    duser = User.objects.get(username=doctorusername)
                    logger.info(f"Redirecting doctor user: {doctorusername}")
                    return redirect('doctor_ui')  # Redirects to the doctor_ui view
                except User.DoesNotExist:
                    logger.error(f"Doctor user does not exist: {doctorusername}")

        # If the user is not authenticated, redirect to a login or home page
        logger.info("User is not authenticated, rendering home.html")
        return render(request, 'homepage/index.html')

from django.shortcuts import render, redirect
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import patient, doctor, consultation, diseaseinfo, rating_review
from chats.models import Chat, Feedback


def admin_ui(request):
    if request.method == 'GET':
        if request.user.is_authenticated and request.user.is_staff:
            auser = request.user
            
            # Get total counts
            total_patients = patient.objects.count()
            total_doctors = doctor.objects.count()
            total_consultations = consultation.objects.count()
            
            # Calculate growth rates (assuming last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            new_patients = patient.objects.filter(user__date_joined__gte=thirty_days_ago).count()
            new_doctors = doctor.objects.filter(user__date_joined__gte=thirty_days_ago).count()
            new_consultations = consultation.objects.filter(consultation_date__gte=thirty_days_ago.date()).count()
            
            patient_growth = (new_patients / total_patients) * 100 if total_patients > 0 else 0
            doctor_growth = (new_doctors / total_doctors) * 100 if total_doctors > 0 else 0
            consultation_growth = (new_consultations / total_consultations) * 100 if total_consultations > 0 else 0
            
            # Get data for user growth trend chart
            user_trend_data = (
                User.objects.filter(date_joined__gte=thirty_days_ago)
                .extra({'date': "date(date_joined)"})
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )
            
            # Get data for consultation distribution chart
            consultation_data = (
                consultation.objects.values('status')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
            
            # Get recent activities
            recent_activities = []
            recent_consultations = consultation.objects.order_by('-consultation_date')[:5]
            for consult in recent_consultations:
                recent_activities.append({
                    'type': 'consultation',
                    'patient': consult.patient.name,
                    'doctor': consult.doctor.name,
                    'date': consult.consultation_date,
                })
            
            recent_reviews = rating_review.objects.order_by('-id')[:5]
            for review in recent_reviews:
                recent_activities.append({
                    'type': 'review',
                    'patient': review.patient.name,
                    'doctor': review.doctor.name,
                    'rating': review.rating,
                    'date': review.doctor.user.date_joined,  # Using doctor's join date as a fallback
                })
            
            # Sort recent activities by date
            # recent_activities.sort(key=lambda x: x['date'], reverse=True)
            # recent_activities = recent_activities[:5]  # Limit to 5 most recent activities
            
            # Get all feedback
            feedback_obj = Feedback.objects.all()
            
            context = {
                "auser": auser,
                "Feedback": feedback_obj,
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_consultations": total_consultations,
                "patient_growth": round(patient_growth, 2),
                "doctor_growth": round(doctor_growth, 2),
                "consultation_growth": round(consultation_growth, 2),
                "user_trend_data": list(user_trend_data),
                "consultation_data": list(consultation_data),
                # "recent_activities": recent_activities,
                'recent_activities': ['hi'],
            }
            
            return render(request, 'admin/admin_ui/admin_ui.html', context)
        else:
            return redirect('home')

    if request.method == 'POST':
        return render(request, 'patient/patient_ui/profile.html')
    
def patient_ui(request):
    if request.method == 'GET':
      if request.user.is_authenticated:
        patientusername = request.session['patientusername']
        puser = User.objects.get(username=patientusername)
        image_path = puser.patient.profile_picture
    

        return render(request,'patient/patient_ui/profile.html' , {"puser":puser, "dp": image_path} )
      else :
        return redirect('home')

    if request.method == 'POST':
       return render(request,'patient/patient_ui/profile.html')      

def pviewprofile(request, patientusername):

    if request.method == 'GET':

          puser = User.objects.get(username=patientusername)
          return render(request,'patient/view_profile/view_profile.html', {"puser":puser})

def checkdisease(request):

  diseaselist=['Fungal infection','Allergy','GERD','Chronic cholestasis','Drug Reaction','Peptic ulcer diseae','AIDS','Diabetes ',
  'Gastroenteritis','Bronchial Asthma','Hypertension ','Migraine','Cervical spondylosis','Paralysis (brain hemorrhage)',
  'Jaundice','Malaria','Chicken pox','Dengue','Typhoid','hepatitis A', 'Hepatitis B', 'Hepatitis C', 'Hepatitis D',
  'Hepatitis E', 'Alcoholic hepatitis','Tuberculosis', 'Common Cold', 'Pneumonia', 'Dimorphic hemmorhoids(piles)',
  'Heart attack', 'Varicose veins','Hypothyroidism', 'Hyperthyroidism', 'Hypoglycemia', 'Osteoarthristis',
  'Arthritis', '(vertigo) Paroymsal  Positional Vertigo','Acne', 'Urinary tract infection', 'Psoriasis', 'Impetigo']
  symptomslist=['itching','skin_rash','nodal_skin_eruptions','continuous_sneezing','shivering','chills','joint_pain',
  'stomach_pain','acidity','ulcers_on_tongue','muscle_wasting','vomiting','burning_micturition','spotting_ urination',
  'fatigue','weight_gain','anxiety','cold_hands_and_feets','mood_swings','weight_loss','restlessness','lethargy',
  'patches_in_throat','irregular_sugar_level','cough','high_fever','sunken_eyes','breathlessness','sweating',
  'dehydration','indigestion','headache','yellowish_skin','dark_urine','nausea','loss_of_appetite','pain_behind_the_eyes',
  'back_pain','constipation','abdominal_pain','diarrhoea','mild_fever','yellow_urine',
  'yellowing_of_eyes','acute_liver_failure','fluid_overload','swelling_of_stomach',
  'swelled_lymph_nodes','malaise','blurred_and_distorted_vision','phlegm','throat_irritation',
  'redness_of_eyes','sinus_pressure','runny_nose','congestion','chest_pain','weakness_in_limbs',
  'fast_heart_rate','pain_during_bowel_movements','pain_in_anal_region','bloody_stool',
  'irritation_in_anus','neck_pain','dizziness','cramps','bruising','obesity','swollen_legs',
  'swollen_blood_vessels','puffy_face_and_eyes','enlarged_thyroid','brittle_nails',
  'swollen_extremeties','excessive_hunger','extra_marital_contacts','drying_and_tingling_lips',
  'slurred_speech','knee_pain','hip_joint_pain','muscle_weakness','stiff_neck','swelling_joints',
  'movement_stiffness','spinning_movements','loss_of_balance','unsteadiness',
  'weakness_of_one_body_side','loss_of_smell','bladder_discomfort','foul_smell_of urine',
  'continuous_feel_of_urine','passage_of_gases','internal_itching','toxic_look_(typhos)',
  'depression','irritability','muscle_pain','altered_sensorium','red_spots_over_body','belly_pain',
  'abnormal_menstruation','dischromic _patches','watering_from_eyes','increased_appetite','polyuria','family_history','mucoid_sputum',
  'rusty_sputum','lack_of_concentration','visual_disturbances','receiving_blood_transfusion',
  'receiving_unsterile_injections','coma','stomach_bleeding','distention_of_abdomen',
  'history_of_alcohol_consumption','fluid_overload','blood_in_sputum','prominent_veins_on_calf',
  'palpitations','painful_walking','pus_filled_pimples','blackheads','scurring','skin_peeling',
  'silver_like_dusting','small_dents_in_nails','inflammatory_nails','blister','red_sore_around_nose',
  'yellow_crust_ooze']

  alphabaticsymptomslist = sorted(symptomslist)

  


  if request.method == 'GET':
    
     return render(request,'patient/checkdisease/checkdisease.html', {"list2":alphabaticsymptomslist})




  elif request.method == 'POST':
       
      ## access you data by playing around with the request.POST object
      
      inputno = int(request.POST["noofsym"])
      print(inputno)
      if (inputno == 0 ) :
          return JsonResponse({'predicteddisease': "none",'confidencescore': 0 })
  
      else :

        psymptoms = []
        psymptoms = request.POST.getlist("symptoms[]")
       
        print(psymptoms)

      
        """      #main code start from here...
        """
      

      
        testingsymptoms = []
        #append zero in all coloumn fields...
        for x in range(0, len(symptomslist)):
          testingsymptoms.append(0)


        #update 1 where symptoms gets matched...
        for k in range(0, len(symptomslist)):

          for z in psymptoms:
              if (z == symptomslist[k]):
                  testingsymptoms[k] = 1


        inputtest = [testingsymptoms]

        print(inputtest)
      

        predicted = model.predict(inputtest)
        print("predicted disease is : ")
        print(predicted)

        y_pred_2 = model.predict_proba(inputtest)
        confidencescore=y_pred_2.max() * 100
        print(" confidence score of : = {0} ".format(confidencescore))

        confidencescore = format(confidencescore, '.0f')
        predicted_disease = predicted[0]

        

        #consult_doctor codes----------

        #   doctor_specialization = ["Rheumatologist","Cardiologist","ENT specialist","Orthopedist","Neurologist",
        #                             "Allergist/Immunologist","Urologist","Dermatologist","Gastroenterologist"]
        

        Rheumatologist = [  'Osteoarthristis','Arthritis']
       
        Cardiologist = [ 'Heart attack','Bronchial Asthma','Hypertension ']
       
        ENT_specialist = ['(vertigo) Paroymsal  Positional Vertigo','Hypothyroidism' ]

        Orthopedist = []

        Neurologist = ['Varicose veins','Paralysis (brain hemorrhage)','Migraine','Cervical spondylosis']

        Allergist_Immunologist = ['Allergy','Pneumonia',
        'AIDS','Common Cold','Tuberculosis','Malaria','Dengue','Typhoid']

        Urologist = [ 'Urinary tract infection',
         'Dimorphic hemmorhoids(piles)']

        Dermatologist = [  'Acne','Chicken pox','Fungal infection','Psoriasis','Impetigo']

        Gastroenterologist = ['Peptic ulcer diseae', 'GERD','Chronic cholestasis','Drug Reaction','Gastroenteritis','Hepatitis E',
        'Alcoholic hepatitis','Jaundice','hepatitis A',
         'Hepatitis B', 'Hepatitis C', 'Hepatitis D','Diabetes ','Hypoglycemia']
         
        if predicted_disease in Rheumatologist :
           consultdoctor = "Rheumatologist"
           
        if predicted_disease in Cardiologist :
           consultdoctor = "Cardiologist"
           

        elif predicted_disease in ENT_specialist :
           consultdoctor = "ENT specialist"
     
        elif predicted_disease in Orthopedist :
           consultdoctor = "Orthopedist"
     
        elif predicted_disease in Neurologist :
           consultdoctor = "Neurologist"
     
        elif predicted_disease in Allergist_Immunologist :
           consultdoctor = "Allergist/Immunologist"
     
        elif predicted_disease in Urologist :
           consultdoctor = "Urologist"
     
        elif predicted_disease in Dermatologist :
           consultdoctor = "Dermatologist"
     
        elif predicted_disease in Gastroenterologist :
           consultdoctor = "Gastroenterologist"
     
        else :
           consultdoctor = "other"


        request.session['doctortype'] = consultdoctor 

        patientusername = request.session['patientusername']
        puser = User.objects.get(username=patientusername)
     

        #saving to database.....................

        patient = puser.patient
        diseasename = predicted_disease
        no_of_symp = inputno
        symptomsname = psymptoms
        confidence = confidencescore

        diseaseinfo_new = diseaseinfo(patient=patient,diseasename=diseasename,no_of_symp=no_of_symp,symptomsname=symptomsname,confidence=confidence,consultdoctor=consultdoctor)
        diseaseinfo_new.save()
        

        request.session['diseaseinfo_id'] = diseaseinfo_new.id

        print("disease record saved sucessfully.............................")

        return JsonResponse({'predicteddisease': predicted_disease ,'confidencescore':confidencescore , "consultdoctor": consultdoctor})

def pconsultation_history(request):

    if request.method == 'GET':

      patientusername = request.session['patientusername']
      puser = User.objects.get(username=patientusername)
      patient_obj = puser.patient
        
      consultationnew = consultation.objects.filter(patient = patient_obj)
      
    
      return render(request,'patient/consultation_history/consultation_history.html',{"consultation":consultationnew})

def dconsultation_history(request):

    if request.method == 'GET':

      doctorusername = request.session['doctorusername']
      duser = User.objects.get(username=doctorusername)
      doctor_obj = duser.doctor
        
      consultationnew = consultation.objects.filter(doctor = doctor_obj)
      
    
      return render(request,'doctor/consultation_history/consultation_history.html',{"consultation":consultationnew})

def doctor_ui(request):

    if request.method == 'GET':

      doctorid = request.session['doctorusername']
      duser = User.objects.get(username=doctorid)
      r = rating_review.objects.filter(doctor=duser.doctor)
      average_rating = r.aggregate(Avg('rating'))['rating__avg']

      # Handle the case where there are no ratings
      if average_rating is None:
          average_rating = 0

      image_path = duser.doctor.profile_picture


      return render(request, 'doctor/doctor_ui/profile.html', {
          "duser": duser,
          "rate": r,
          "average_rating": round(average_rating, 1), 
          "dp": image_path
            # Round to one decimal place if needed
      })
    
def dviewprofile(request, doctorusername):

    if request.method == 'GET':

         duser = User.objects.get(username=doctorusername)
         r = rating_review.objects.filter(doctor=duser.doctor)
         average_rating = r.aggregate(Avg('rating'))['rating__avg']
         if average_rating == None:
            average_rating = 0
         image_path = duser.doctor.profile_picture
         return render(request,'doctor/view_profile/view_profile.html', {"duser":duser, "rate":r, "average_rating": round(average_rating, 1), "dp": image_path  } )
    
def consult_a_doctor(request):


    if request.method == 'GET':

        
        doctortype = request.session['doctortype']
        print(doctortype)
        dobj = doctor.objects.all()
        #dobj = doctor.objects.filter(specialization=doctortype)


        return render(request,'patient/consult_a_doctor/consult_a_doctor.html',{"dobj":dobj})

def make_consultation(request, doctorusername):

    if request.method == 'POST':
       

        patientusername = request.session['patientusername']
        puser = User.objects.get(username=patientusername)
        patient_obj = puser.patient
        
        
        #doctorusername = request.session['doctorusername']
        duser = User.objects.get(username=doctorusername)
        doctor_obj = duser.doctor
        request.session['doctorusername'] = doctorusername


        diseaseinfo_id = request.session['diseaseinfo_id']
        diseaseinfo_obj = diseaseinfo.objects.get(id=diseaseinfo_id)

        consultation_date = date.today()
        status = "active"
        
        consultation_new = consultation( patient=patient_obj, doctor=doctor_obj, diseaseinfo=diseaseinfo_obj, consultation_date=consultation_date,status=status)
        consultation_new.save()

        request.session['consultation_id'] = consultation_new.id

        print("consultation record is saved sucessfully.............................")

         
        return redirect('consultationview',consultation_new.id)

def consultationview(request,consultation_id):
   
    if request.method == 'GET':

   
      request.session['consultation_id'] = consultation_id
      consultation_obj = consultation.objects.get(id=consultation_id)

      return render(request,'consultation/consultation.html', {"consultation":consultation_obj })

   #  if request.method == 'POST':
   #    return render(request,'consultation/consultation.html' )

def rate_review(request,consultation_id):
   if request.method == "POST":
         
         consultation_obj = consultation.objects.get(id=consultation_id)
         patient = consultation_obj.patient
         doctor1 = consultation_obj.doctor
         rating = request.POST.get('rating')
         review = request.POST.get('review')

         rating_obj = rating_review(patient=patient,doctor=doctor1,rating=rating,review=review)
         rating_obj.save()

         rate = int(rating_obj.rating_is)
         doctor.objects.filter(pk=doctor1).update(rating=rate)
         

         return redirect('consultationview',consultation_id)

def close_consultation(request,consultation_id):
   if request.method == "POST":
         
         consultation.objects.filter(pk=consultation_id).update(status="closed")
         
         return redirect('home')

def post(request):
    if request.method == "POST":
        msg = request.POST.get('msgbox', None)

        consultation_id = request.session['consultation_id'] 
        consultation_obj = consultation.objects.get(id=consultation_id)

        c = Chat(consultation_id=consultation_obj,sender=request.user, message=msg)

        #msg = c.user.username+": "+msg

        if msg != '':            
            c.save()
            print("msg saved"+ msg )
            return JsonResponse({ 'msg': msg })
    else:
        return HttpResponse('Request must be POST.')

def chat_messages(request):
   if request.method == "GET":

         consultation_id = request.session['consultation_id'] 

         c = Chat.objects.filter(consultation_id=consultation_id)
         return render(request, 'consultation/chat_body.html', {'chat': c})


