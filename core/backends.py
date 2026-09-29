from django.contrib.auth.backends import ModelBackend

from .models import PhoneNumber


class PhoneNumberBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, phone_number=None, **kwargs):
        identifier = phone_number or username
        if not identifier or password is None:
            return None

        try:
            profile = PhoneNumber.objects.select_related('user').get(phone_number=identifier)
        except PhoneNumber.DoesNotExist:
            return super().authenticate(
                request,
                username=identifier,
                password=password,
                **kwargs,
            )

        user = profile.user
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None