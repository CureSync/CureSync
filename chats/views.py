from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from .models import Chat, Feedback
from main_app.views import patient_ui, doctor_ui
from main_app.models import patient, doctor

# View to handle feedback submission
def post_feedback(request):
    if request.method == "POST":
        feedback = request.POST.get('feedback', None)
        if feedback:
            f = Feedback(sender=request.user, feedback=feedback)
            f.save()
            print(feedback)
            
            # Check if the user is a patient or a doctor
            try:
                if request.user.patient.is_patient:
                    return HttpResponse("Feedback successfully sent.")
            except:
                pass
            if request.user.doctor.is_doctor:
                return HttpResponse("Feedback successfully sent.")
        else:
            return HttpResponse("Feedback field is empty.")

# View to handle feedback retrieval
def get_feedback(request):
    if request.method == "GET":
        obj = Feedback.objects.all()
        return render(request, 'consultation/chat_body.html', {"obj": obj})

# -------------------------------- Chatting System --------------------------------

# Uncomment the below code to enable the chat functionality

# View to handle message posting in chat
# def post(request):
#     if request.method == "POST":
#         msg = request.POST.get('msgbox', None)
#         consultation_id = request.session['consultation_id']
#         consultation_obj = consultation.objects.get(id=consultation_id)
#         c = Chat(consultation_id=consultation_obj, sender=request.user, message=msg)
#         if msg:
#             c.save()
#             print("Message saved: " + msg)
#             return JsonResponse({'msg': msg})
#     else:
#         return HttpResponse('Request must be POST.')

# View to retrieve chat messages
# def messages(request):
#     if request.method == "GET":
#         consultation_id = request.session['consultation_id']
#         c = Chat.objects.filter(consultation_id=consultation_id)
#         return render(request, 'consultation/chat_body.html', {'chat': c})
