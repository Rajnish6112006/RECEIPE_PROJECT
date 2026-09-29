from django.contrib import admin
from django.urls import path
from core.forms import PhoneNumberAdminAuthenticationForm
from core.views import (
    delete_receipe,
    department_create,
    login_view,
    logout_view,
    receipes,
    register_view,
    student_list,
    student_results,
    update_receipe,
)
from django.conf import settings
from django.conf.urls.static import static

admin.site.login_form = PhoneNumberAdminAuthenticationForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', receipes, name="receipes"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('students/', student_list, name='students'),
    path('students/<int:student_id>/results/', student_results, name='student_results'),
    path('departments/create/', department_create, name='department_create'),
    path('delete/<int:id>/', delete_receipe, name="delete_receipe"),
    path('update/<int:id>/', update_receipe, name="update_receipe"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)