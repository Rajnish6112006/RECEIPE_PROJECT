import logging
from io import BytesIO
from smtplib import SMTPException

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import CharField, F, Q, Sum, Window
from django.db.models.functions import Cast, Coalesce, Rank
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from .forms import DepartmentForm, PhoneNumberRegistrationForm
from .models import *

logger = logging.getLogger(__name__)


def _create_report_card_pdf(student, marks):
    buffer = BytesIO()
    page_width, page_height = A4
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = page_height - 54

    pdf.setTitle(f'Report card - {student.student_name}')
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(48, y, 'Student Report Card')
    y -= 34

    pdf.setFont('Helvetica', 11)
    details = [
        f'Student: {student.student_name}',
        f'Student ID: {student.student_id.student_id}',
        f'Rank: {student.rank}',
        f'Total marks: {student.total_marks}',
        f'Result date: {student.report_card.result_date.strftime("%B %d, %Y")}',
    ]
    for detail in details:
        pdf.drawString(48, y, detail)
        y -= 20

    y -= 12
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(48, y, '#')
    pdf.drawString(82, y, 'Subject')
    pdf.drawRightString(page_width - 48, y, 'Marks')
    y -= 8
    pdf.line(48, y, page_width - 48, y)
    y -= 20

    pdf.setFont('Helvetica', 10)
    for index, mark in enumerate(marks, start=1):
        subject_lines = simpleSplit(mark.subject.subject_name, 'Helvetica', 10, page_width - 170)
        for line_index, line in enumerate(subject_lines):
            if y < 54:
                pdf.showPage()
                pdf.setFont('Helvetica', 10)
                y = page_height - 54
            if line_index == 0:
                pdf.drawString(48, y, str(index))
                pdf.drawRightString(page_width - 48, y, str(mark.marks))
            pdf.drawString(82, y, line)
            y -= 16

    pdf.save()
    return buffer.getvalue()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('receipes')

    form = PhoneNumberRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('receipes')

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('receipes')

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        user = authenticate(request, phone_number=phone_number, password=password)

        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'receipes'))

        messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required
def receipes(request):

    # ADD RECEIPE
    if request.method == "POST":
        data = request.POST
        receipe_image = request.FILES.get('receipe_image')

        Receipe.objects.create(
            receipe_name=data.get('receipe_name'),
            receipe_desc=data.get('receipe_desc'),
            receipe_image=receipe_image
        )
        return redirect('/')

    queryset = Receipe.objects.all()

    # SEARCH
    if request.GET.get('search'):
        queryset = queryset.filter(
            receipe_name__icontains=request.GET.get('search')
        )

    context = {'receipes': queryset}
    return render(request, 'receipes.html', context)


@login_required
def delete_receipe(request, id):
    queryset = Receipe.objects.get(id=id)
    queryset.delete()
    return redirect('/')


@login_required
def update_receipe(request, id):
    queryset = Receipe.objects.get(id=id)

    if request.method == "POST":
        data = request.POST
        receipe_image = request.FILES.get('receipe_image')

        queryset.receipe_name = data.get('receipe_name')
        queryset.receipe_desc = data.get('receipe_desc')

        if receipe_image:
            queryset.receipe_image = receipe_image

        queryset.save()
        return redirect('/')

    context = {'receipe': queryset}
    return render(request, 'update.html', context)


@login_required
def student_list(request):
    students = Student.student_list()
    search_query = request.GET.get('search', '').strip()
    if search_query:
        students = students.annotate(
            searchable_age=Cast('student_age', output_field=CharField())
        ).filter(
            Q(student_name__icontains=search_query)
            | Q(student_email__icontains=search_query)
            | Q(student_address__icontains=search_query)
            | Q(department__department_name__icontains=search_query)
            | Q(student_id__student_id__icontains=search_query)
            | Q(searchable_age__icontains=search_query)
        )

    stats = Student.student_stats()
    context = {
        'students': students,
        'stats': stats,
        'search_query': search_query,
    }
    return render(request, 'students.html', context)


@login_required
def student_results(request, student_id):
    ranked_students = Student.objects.annotate(
        total_marks=Coalesce(Sum('studentmarks__marks'), 0)
    ).annotate(
        rank=Window(expression=Rank(), order_by=F('total_marks').desc())
    )
    student = get_object_or_404(
        ranked_students.select_related('department', 'student_id'),
        pk=student_id,
    )
    report_card = ReportCard.objects.filter(student=student).first()
    marks = list(
        student.studentmarks.select_related('subject').order_by('subject__subject_name')
    )

    if request.method == 'POST' and (
        'generate_report' in request.POST or 'send_report' in request.POST
    ):
        if 'generate_report' in request.POST:
            report_card, _ = ReportCard.objects.get_or_create(student=student)

        if report_card is None:
            messages.error(request, 'Generate the report card before sending it.')
        elif not student.student_email:
            messages.warning(request, 'Add a student email address before sending the report card.')
        else:
            mark_lines = [
                f'{mark.subject.subject_name}: {mark.marks}'
                for mark in marks
            ]
            email_body = '\n'.join([
                f'Student: {student.student_name}',
                f'Student ID: {student.student_id.student_id}',
                f'Rank: {student.rank}',
                f'Total marks: {student.total_marks}',
                f'Result date: {report_card.result_date.strftime("%B %d, %Y")}',
                '',
                'Subject marks:',
                *mark_lines,
            ])
            try:
                email = EmailMessage(
                    subject=f'Report card for {student.student_name}',
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[student.student_email],
                )
                email.attach(
                    f'report-card-{student.student_id.student_id}.pdf',
                    _create_report_card_pdf(student, marks),
                    'application/pdf',
                )
                sent = email.send(fail_silently=False)
            except (OSError, SMTPException):
                logger.exception('Could not send a report card email for student %s.', student.pk)
                messages.error(request, 'Report card saved, but the email could not be sent. Please retry.')
            else:
                if sent:
                    messages.success(request, f'Report card sent to {student.student_email}.')
                else:
                    messages.error(request, 'Report card saved, but the email could not be sent. Please retry.')

        return redirect('student_results', student_id=student.pk)

    return render(request, 'student_results.html', {
        'student': student,
        'marks': marks,
        'report_card': report_card,
    })


@login_required
def department_create(request):
    form = DepartmentForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('department_create')

    context = {
        'form': form,
        'departments': Department.objects.all(),
    }
    return render(request, 'department_create.html', context)

# Create your views here.
