from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Avg, Count, Max, Min


class Receipe(models.Model):
    receipe_name = models.CharField(max_length=200)
    receipe_desc = models.TextField()
    receipe_image = models.ImageField(upload_to="receipes")

    def __str__(self):
        return self.receipe_name


class Department(models.Model):
    department_name = models.CharField(max_length=100, unique=True)

    @classmethod
    def department_summary(cls):
        return (
            cls.objects.annotate(
                student_count=Count('student'),
                average_age=Avg('student__student_age'),
            )
            .order_by('department_name')
            .values('department_name', 'student_count', 'average_age')
        )

    def __str__(self):
        return self.department_name


class StudentID(models.Model):
    student_id = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.student_id


class Subject(models.Model):
    subject_name = models.CharField(max_length=100)

    def __str__(self):
        return self.subject_name


class Student(models.Model):
    student_name = models.CharField(max_length=120)
    student_email = models.EmailField(blank=True)
    student_age = models.PositiveSmallIntegerField(null=True, blank=True)
    student_address = models.TextField(blank=True)
    student_id = models.OneToOneField(StudentID, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    @classmethod
    def student_list(cls):
        return cls.objects.select_related('department', 'student_id').all()

    @classmethod
    def student_stats(cls):
        return cls.objects.aggregate(
            total_students=Count('id'),
            average_age=Avg('student_age'),
            max_age=Max('student_age'),
            min_age=Min('student_age'),
        )

    def __str__(self):
        return self.student_name

    class Meta:
        ordering = ['student_name']
        verbose_name = 'student'


class SubjectMarks(models.Model):
    student = models.ForeignKey(Student, related_name='studentmarks', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.IntegerField()

    def __str__(self):
        return f'{self.student.student_name} - {self.subject.subject_name}'

    class Meta:
        unique_together = ('student', 'subject')


class ReportCard(models.Model):
    student = models.OneToOneField(Student, related_name='report_card', on_delete=models.CASCADE)
    result_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'Report card - {self.student.student_name}'


class PhoneNumber(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(
        max_length=16,
        unique=True,
        validators=[RegexValidator(r'^\+?[0-9]{10,15}$', 'Enter a valid phone number.')],
    )

    def __str__(self):
        return self.phone_number
                
