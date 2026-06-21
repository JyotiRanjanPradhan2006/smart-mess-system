"""
Run: python setup_menu.py
Sets up demo food items for all sessions including NonVeg Breakfast.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mess_system.settings')
import django
django.setup()

from meals.models import MenuConfig, MealPrice
import datetime

today = datetime.date.today()

menu_data = {
    'breakfast': {
        'has_veg':      True,
        'has_nonveg':   True,
        'veg_items':    'Idli, Sambar, Coconut Chutney, Vada, Tea/Coffee',
        'nonveg_items': 'Egg Bhurji, Bread Toast, Boiled Eggs, Tea/Coffee',
        'description':  'Morning Breakfast',
    },
    'lunch': {
        'has_veg':      True,
        'has_nonveg':   True,
        'veg_items':    'Dal Makhani, Jeera Rice, Roti, Mix Veg Sabzi, Salad, Curd',
        'nonveg_items': 'Chicken Curry, Steamed Rice, Roti, Onion Salad, Raita',
        'description':  'Afternoon Lunch',
    },
    'dinner': {
        'has_veg':      True,
        'has_nonveg':   True,
        'veg_items':    'Paneer Butter Masala, Rice, Roti, Dal Fry, Kheer',
        'nonveg_items': 'Mutton Curry, Rice, Roti, Raita, Papad',
        'description':  'Evening Dinner',
    },
}

for session, data in menu_data.items():
    obj, created = MenuConfig.objects.update_or_create(
        effective_date=today,
        meal_session=session,
        defaults={
            'has_veg':      data['has_veg'],
            'has_nonveg':   data['has_nonveg'],
            'veg_items':    data['veg_items'],
            'nonveg_items': data['nonveg_items'],
            'description':  data['description'],
            'is_active':    True,
        }
    )
    action = 'Created' if created else 'Updated'
    print(f"{action} {session}: Veg={data['has_veg']}, NonVeg={data['has_nonveg']}")

# Add NonVeg Breakfast price if missing
MealPrice.objects.get_or_create(
    meal_type='nonveg',
    meal_session='breakfast',
    effective_from=today,
    defaults={'price': 50}
)
print("NonVeg Breakfast price set: Rs.50")
print("\nAll done! Refresh your dashboard to see food names.")