from faker import Faker
import random
from .models import *

fake = Faker()


def seed_db(n=10) -> None:
    try:
        departments_objs = list(Department.objects.all())
        if not departments_objs:
            raise ValueError('No departments found. Please create departments first.')

        created = 0
        while created < n:
            student_id_value = f'STU-0{random.randint(100, 999)}'
            if StudentID.objects.filter(student_id=student_id_value).exists():
                continue

            department = random.choice(departments_objs)
            student_name = fake.name()
            student_email = fake.email()
            student_age = random.randint(20, 30)
            student_address = fake.address()

            student_id_obj = StudentID.objects.create(student_id=student_id_value)
            Student.objects.create(
                department=department,
                student_id=student_id_obj,
                student_name=student_name,
                student_email=student_email,
                student_age=student_age,
                student_address=student_address,
            )
            created += 1

    except Exception as e:
        print(e)

   

