"""
python manage.py seed_demo
Creates demo admin, staff, and 3 student accounts with menu/price configs.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = 'Seed demo data for the Smart Mess system'

    def handle(self, *args, **kwargs):
        from accounts.models import User, StudentProfile, SystemConfig
        from meals.models import MenuConfig, MealPrice

        self.stdout.write('🌱 Seeding demo data...')

        # ── System config ────────────────────────────────────────────────────
        cfg = SystemConfig.get_solo()
        cfg.pending_limit = 3000
        cfg.warning_fraction = 0.667
        cfg.booking_deadline_hour = 9
        cfg.save()
        self.stdout.write('  ✅ SystemConfig set')

        # ── Admin user ───────────────────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin', password='admin123',
                email='admin@mess.com',
                first_name='Mess', last_name='Admin',
            )
            admin.role = User.Role.ADMIN
            admin.save()
            self.stdout.write('  ✅ Admin user: admin / admin123')

        # ── Staff user ───────────────────────────────────────────────────────
        if not User.objects.filter(username='staff1').exists():
            staff = User.objects.create_user(
                username='staff1', password='staff123',
                first_name='Ramu', last_name='Kaka',
            )
            staff.role = User.Role.STAFF
            staff.is_staff = False
            staff.save()
            self.stdout.write('  ✅ Staff user: staff1 / staff123')

        # ── Students ─────────────────────────────────────────────────────────
        students_data = [
            ('stu1', 'stu123', 'Arjun', 'Sharma', 'CS2021001', 'Computer Science', 3),
            ('stu2', 'stu123', 'Priya', 'Patel',  'EC2021042', 'Electronics', 3),
            ('stu3', 'stu123', 'Rahul', 'Verma',  'ME2022015', 'Mechanical', 2),
        ]
        for uname, pwd, fn, ln, roll, dept, yr in students_data:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(
                    username=uname, password=pwd,
                    first_name=fn, last_name=ln,
                    email=f'{uname}@student.mess.com',
                )
                u.role = User.Role.STUDENT
                u.save()
                StudentProfile.objects.create(
                    user=u, roll_number=roll, department=dept,
                    year_of_study=yr,
                    registration_status=StudentProfile.RegistrationStatus.APPROVED,
                )
                self.stdout.write(f'  ✅ Student: {uname} / {pwd} ({roll})')

        # ── Menu configs ─────────────────────────────────────────────────────
        today = timezone.localdate()
        for session in ['breakfast', 'lunch', 'dinner']:
            MenuConfig.objects.get_or_create(
                effective_date=today - datetime.timedelta(days=30),
                meal_session=session,
                defaults={
                    'has_veg': True, 'has_nonveg': True if session == 'lunch' else False,
                    'description': f'Standard {session} menu',
                    'is_active': True,
                }
            )
        self.stdout.write('  ✅ Menu configs set')

        # ── Prices ───────────────────────────────────────────────────────────
        price_data = [
            ('veg',    'breakfast', 30),
            ('veg',    'lunch',     60),
            ('veg',    'dinner',    50),
            ('nonveg', 'lunch',     90),
        ]
        for mtype, session, price in price_data:
            MealPrice.objects.get_or_create(
                meal_type=mtype, meal_session=session,
                effective_from=today - datetime.timedelta(days=30),
                defaults={'price': price}
            )
        self.stdout.write('  ✅ Meal prices set')

        self.stdout.write(self.style.SUCCESS('\n🎉 Demo seeding complete!\n'))
        self.stdout.write('  Admin:  admin   / admin123')
        self.stdout.write('  Staff:  staff1  / staff123')
        self.stdout.write('  Student: stu1, stu2, stu3 / stu123\n')
