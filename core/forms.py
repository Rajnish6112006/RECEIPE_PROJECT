from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import Department, PhoneNumber


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('department_name',)
        labels = {'department_name': 'Department name'}
        widgets = {
            'department_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department name',
            }),
        }


class PhoneNumberRegistrationForm(forms.Form):
    phone_number = forms.CharField(
        label='Mobile number',
        max_length=16,
        validators=[RegexValidator(r'^\+?[0-9]{10,15}$', 'Enter a valid phone number.')],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9876543210',
            'autocomplete': 'tel',
        }),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number'].strip()
        if PhoneNumber.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError('An account with this mobile number already exists.')
        if get_user_model().objects.filter(username=phone_number).exists():
            raise forms.ValidationError('An account with this mobile number already exists.')
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password1')
        confirmation = cleaned_data.get('password2')
        phone_number = cleaned_data.get('phone_number')

        if password and confirmation and password != confirmation:
            self.add_error('password2', 'The passwords do not match.')
        if password and phone_number:
            user = get_user_model()(username=phone_number)
            try:
                validate_password(password, user=user)
            except ValidationError as error:
                self.add_error('password1', error)
        return cleaned_data

    def save(self):
        phone_number = self.cleaned_data['phone_number']
        user = get_user_model().objects.create_user(
            username=phone_number,
            password=self.cleaned_data['password1'],
        )
        PhoneNumber.objects.create(user=user, phone_number=phone_number)
        return user


class PhoneNumberAdminAuthenticationForm(AdminAuthenticationForm):
    username = forms.CharField(
        label='Phone number',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'tel'}),
    )
