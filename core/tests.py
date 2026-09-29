from django.contrib import admin
from django.test import RequestFactory
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Max, Min
from django.core import mail
from django.test import override_settings

from .admin import ReportCardAdmin
from .models import Department, PhoneNumber, ReportCard, Student, StudentID, Subject, SubjectMarks


class StudentAggregationAndAnnotationTests(TestCase):
    def setUp(self):
        self.cs = Department.objects.create(department_name='CS')
        self.ece = Department.objects.create(department_name='ECE')

        s1 = StudentID.objects.create(student_id='S-001')
        s2 = StudentID.objects.create(student_id='S-002')
        s3 = StudentID.objects.create(student_id='S-003')
        s4 = StudentID.objects.create(student_id='S-004')

        Student.objects.create(
            student_name='Alice', student_email='alice@example.com',
            student_age=20, student_address='Delhi', student_id=s1, department=self.cs
        )
        Student.objects.create(
            student_name='Bob', student_email='bob@example.com',
            student_age=22, student_address='Noida', student_id=s2, department=self.cs
        )
        Student.objects.create(
            student_name='Charlie', student_email='charlie@example.com',
            student_age=25, student_address='Lucknow', student_id=s3, department=self.ece
        )
        Student.objects.create(
            student_name='Diana', student_email='diana@example.com',
            student_age=30, student_address='Jaipur', student_id=s4, department=self.ece
        )

    def test_student_stats_aggregation(self):
        stats = Student.student_stats()

        self.assertEqual(stats['total_students'], 4)
        self.assertAlmostEqual(stats['average_age'], 24.25)
        self.assertEqual(stats['max_age'], 30)
        self.assertEqual(stats['min_age'], 20)

    def test_department_student_summary_annotation(self):
        summary = list(Department.department_summary())

        self.assertEqual(summary[0]['department_name'], 'CS')
        self.assertEqual(summary[0]['student_count'], 2)
        self.assertAlmostEqual(summary[0]['average_age'], 21.0)

        self.assertEqual(summary[1]['department_name'], 'ECE')
        self.assertEqual(summary[1]['student_count'], 2)
        self.assertAlmostEqual(summary[1]['average_age'], 27.5)


class StudentSearchTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_user(username='search-user'))
        department = Department.objects.create(department_name='Computer Science')
        student_id = StudentID.objects.create(student_id='STU-2048')
        Student.objects.create(
            student_name='Maya Sen',
            student_email='maya@example.com',
            student_age=23,
            student_address='Kolkata',
            student_id=student_id,
            department=department,
        )

    def test_search_matches_every_student_table_field(self):
        for query in ('Maya', 'maya@example.com', 'Kolkata', 'Computer Science', 'STU-2048', '3'):
            with self.subTest(query=query):
                response = self.client.get('/students/', {'search': query})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context['students']), 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class StudentResultsTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_user(username='results-user'))
        student_id = StudentID.objects.create(student_id='STU-310')
        self.student = Student.objects.create(
            student_name='Asha Rao',
            student_email='asha@example.com',
            student_id=student_id,
        )
        scores = {
            'Maths': 20,
            'Science': 84,
            'Computer Science': 76,
            'DSA': 21,
            'C++': 73,
            'Java': 36,
        }
        for subject_name, marks in scores.items():
            subject = Subject.objects.create(subject_name=subject_name)
            SubjectMarks.objects.create(student=self.student, subject=subject, marks=marks)

    def test_results_show_sum_of_marks_and_rank(self):
        response = self.client.get('/students/{}/results/'.format(self.student.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'].total_marks, 310)
        self.assertEqual(response.context['student'].rank, 1)
        self.assertEqual(len(response.context['marks']), 6)

    def test_generating_report_card_saves_result_date(self):
        response = self.client.post(
            '/students/{}/results/'.format(self.student.pk),
            {'generate_report': '1'},
        )

        self.assertRedirects(response, '/students/{}/results/'.format(self.student.pk))
        report_card = ReportCard.objects.get(student=self.student)
        self.assertIsNotNone(report_card.result_date)

    def test_generating_report_card_emails_marks_total_and_rank(self):
        response = self.client.post(
            '/students/{}/results/'.format(self.student.pk),
            {'generate_report': '1'},
        )

        self.assertRedirects(response, '/students/{}/results/'.format(self.student.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['asha@example.com'])
        self.assertIn('Rank: 1', mail.outbox[0].body)
        self.assertIn('Total marks: 310', mail.outbox[0].body)
        self.assertIn('Maths: 20', mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        filename, attachment, content_type = mail.outbox[0].attachments[0]
        self.assertEqual(filename, 'report-card-STU-310.pdf')
        self.assertEqual(content_type, 'application/pdf')
        self.assertTrue(attachment.startswith(b'%PDF'))

    def test_report_email_can_be_retried(self):
        ReportCard.objects.create(student=self.student)

        response = self.client.post(
            '/students/{}/results/'.format(self.student.pk),
            {'send_report': '1'},
        )

        self.assertRedirects(response, '/students/{}/results/'.format(self.student.pk))
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_report_card_list_calculates_total_and_rank(self):
        report_card = ReportCard.objects.create(student=self.student)
        model_admin = ReportCardAdmin(ReportCard, admin.site)

        row = model_admin.get_queryset(RequestFactory().get('/admin/core/reportcard/')).get(
            pk=report_card.pk
        )

        self.assertEqual(row.total_marks, 310)
        self.assertEqual(row.student_rank, 1)


class PhoneNumberLoginTests(TestCase):
    def test_registered_user_can_login_with_phone_number(self):
        response = self.client.post('/register/', {
            'phone_number': '9876543210',
            'password1': 'SecurePass!482',
            'password2': 'SecurePass!482',
        })

        self.assertRedirects(response, '/')
        user = get_user_model().objects.get(username='9876543210')
        self.assertTrue(self.client.session.get('_auth_user_id'))
        self.assertTrue(PhoneNumber.objects.filter(user=user, phone_number='9876543210').exists())

    def test_site_login_accepts_phone_number(self):
        user = get_user_model().objects.create_user(
            username='9876543210',
            password='SecurePass!482',
        )
        profile = PhoneNumber.objects.create(user=user, phone_number='9876543210')

        response = self.client.post('/login/', {
            'phone_number': profile.phone_number,
            'password': 'SecurePass!482',
        })

        self.assertRedirects(response, '/')
        self.assertEqual(self.client.session.get('_auth_user_id'), str(profile.user.pk))

    def test_admin_login_uses_phone_number_label_and_authentication(self):
        user = get_user_model().objects.create_superuser(
            username='admin-phone-test',
            email='admin@example.com',
            password='SecurePass!482',
        )
        PhoneNumber.objects.create(user=user, phone_number='9876543210')

        login_page = self.client.get('/admin/login/')
        response = self.client.post('/admin/login/', {
            'username': '9876543210',
            'password': 'SecurePass!482',
            'next': '/admin/',
        })

        self.assertEqual(login_page.context['form'].fields['username'].label, 'Phone number')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/')
