"""
Run: python setup_daymenu.py
Seeds 7-day different menus for each day of week.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mess_system.settings')
import django
django.setup()

from meals.models import DayWiseMenu, MealPrice
import datetime

# Different menu for each day of week
# day_of_week: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

day_menus = {
    0: {  # Monday
        'breakfast': ('Poha, Jalebi, Tea/Coffee',           'Egg Bhurji, Bread Toast, Tea'),
        'lunch':     ('Dal Tadka, Rice, Roti, Aloo Gobi',   'Fish Curry, Rice, Roti, Salad'),
        'dinner':    ('Rajma Rice, Roti, Curd, Papad',      'Chicken Biryani, Raita, Papad'),
    },
    1: {  # Tuesday
        'breakfast': ('Upma, Coconut Chutney, Tea',         'Boiled Eggs, Bread, Butter, Tea'),
        'lunch':     ('Chole, Rice, Roti, Jeera Aloo',      'Mutton Curry, Rice, Roti, Onion Salad'),
        'dinner':    ('Paneer Butter Masala, Roti, Rice',   'Egg Curry, Rice, Roti, Raita'),
    },
    2: {  # Wednesday
        'breakfast': ('Idli, Sambar, Chutney, Vada',        'Egg Bhurji, Paratha, Tea'),
        'lunch':     ('Dal Makhani, Jeera Rice, Roti',      'Chicken Curry, Rice, Roti, Salad'),
        'dinner':    ('Mix Veg, Dal Fry, Rice, Roti',       'Fish Fry, Rice, Roti, Lemon'),
    },
    3: {  # Thursday
        'breakfast': ('Paratha, Curd, Pickle, Tea',         'Omelette, Bread Toast, Tea'),
        'lunch':     ('Sambar Rice, Papad, Curd, Pickle',   'Mutton Biryani, Raita, Salad'),
        'dinner':    ('Palak Paneer, Rice, Roti, Dal',      'Chicken Masala, Rice, Roti'),
    },
    4: {  # Friday
        'breakfast': ('Dosa, Sambar, Chutney, Tea',         'Egg Dosa, Sambar, Tea'),
        'lunch':     ('Pav Bhaji, Rice, Roti, Salad',       'Fish Curry, Rice, Roti, Papad'),
        'dinner':    ('Shahi Paneer, Naan, Rice, Dal',      'Chicken Biryani, Raita, Salan'),
    },
    5: {  # Saturday
        'breakfast': ('Chole Bhature, Tea/Coffee',          'Egg Curry, Bread, Tea'),
        'lunch':     ('Veg Biryani, Raita, Papad, Salad',   'Mutton Rogan Josh, Rice, Roti'),
        'dinner':    ('Dal Baati, Churma, Rice, Curd',      'BBQ Chicken, Rice, Roti, Salad'),
    },
    6: {  # Sunday
        'breakfast': ('Puri Sabzi, Halwa, Tea/Coffee',      'Egg Paratha, Curd, Tea'),
        'lunch':     ('Special Thali: Dal, Sabzi, Roti, Rice, Kheer', 'Chicken Biryani, Curry, Raita'),
        'dinner':    ('Paneer Tikka, Naan, Dal, Rice',      'Mutton Curry, Rice, Naan, Raita'),
    },
}

session_map = {'breakfast': 'breakfast', 'lunch': 'lunch', 'dinner': 'dinner'}
day_names   = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

for day_num, sessions in day_menus.items():
    for session, (veg, nonveg) in sessions.items():
        obj, created = DayWiseMenu.objects.update_or_create(
            day_of_week=day_num,
            meal_session=session,
            defaults={
                'has_veg':      True,
                'has_nonveg':   True,
                'veg_items':    veg,
                'nonveg_items': nonveg,
                'is_active':    True,
            }
        )
        action = 'Created' if created else 'Updated'
        print(f"  {action}: {day_names[day_num]} {session}")

# Add NonVeg Breakfast price if missing
today = datetime.date.today()
MealPrice.objects.get_or_create(
    meal_type='nonveg', meal_session='breakfast',
    effective_from=today, defaults={'price': 50}
)
print("\nNonVeg Breakfast price: Rs.50")
print("\nAll 7-day menus set! Each day now has different food items.")
print("Refresh your dashboard to see the changes.")