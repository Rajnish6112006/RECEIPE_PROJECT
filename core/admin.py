from django.contrib import admin
from django.db.models import F, IntegerField, OuterRef, Sum, Subquery, Value, Window
from django.db.models.functions import Coalesce, Rank
from .models import Department, PhoneNumber, Receipe, ReportCard, Student, StudentID, Subject, SubjectMarks


@admin.register(Receipe)
class ReceipeAdmin(admin.ModelAdmin):
	list_display = ('receipe_name', 'receipe_desc')
	search_fields = ('receipe_name', 'receipe_desc')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
	list_display = ('department_name',)
	search_fields = ('department_name',)


@admin.register(StudentID)
class StudentIDAdmin(admin.ModelAdmin):
	list_display = ('student_id',)
	search_fields = ('student_id',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('student_name', 'student_email', 'student_id', 'department')
	list_filter = ('department',)
	search_fields = ('student_name', 'student_email', 'student_id__student_id')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
	search_fields = ('subject_name',)


@admin.register(SubjectMarks)
class SubjectMarksAdmin(admin.ModelAdmin):
	list_display = ('student', 'subject', 'marks')
	list_filter = ('subject',)
	search_fields = ('student__student_name', 'subject__subject_name')


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
	list_display = ('student', 'display_rank', 'display_total_marks', 'result_date')
	readonly_fields = ('result_date',)
	search_fields = ('student__student_name', 'student__student_id__student_id')

	def get_queryset(self, request):
		queryset = super().get_queryset(request).select_related('student')
		totals = SubjectMarks.objects.filter(student_id=OuterRef('student_id')).order_by().values('student_id')
		totals = totals.annotate(total=Sum('marks')).values('total')[:1]
		return queryset.annotate(
			total_marks=Coalesce(Subquery(totals, output_field=IntegerField()), Value(0))
		).annotate(
			student_rank=Window(expression=Rank(), order_by=F('total_marks').desc())
		)

	@admin.display(description='Student rank', ordering='student_rank')
	def display_rank(self, obj):
		return obj.student_rank

	@admin.display(description='Total marks', ordering='total_marks')
	def display_total_marks(self, obj):
		return obj.total_marks


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
	list_display = ('phone_number', 'user')
	search_fields = ('phone_number', 'user__username')