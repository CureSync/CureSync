from django.contrib import admin
from django.urls import path,include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
     path('admin/', admin.site.urls),
     path("", include("main_app.urls")),
     path("accounts/", include("accounts.urls")),
     path("", include("chats.urls"))
]

urlpatterns += staticfiles_urlpatterns()
