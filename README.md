# 🍽️ Smart Mess Meal Scheduling & Billing System

A fully-featured Django web application for hostel/college mess management.

---

## 📋 Features

| Module | Description |
|--------|-------------|
| **User & Card Management** | Student registration → Admin approval → QR card issuance |
| **Dynamic Menu Scheduling** | Admin sets veg/non-veg availability per session; students schedule accordingly |
| **Automated Booking Engine** | Weekly schedule generates 4 weeks of daily bookings automatically |
| **QR Attendance** | Staff scans static QR → system auto-validates & marks attendance |
| **Billing & Monitoring** | Monthly bills, pending threshold warnings, automatic card blocking |
| **Notification System** | In-app alerts for menu changes, price updates, warnings, card status |
| **Menu Governance** | Menu/price changes trigger full schedule invalidation + student notifications |
| **Revenue Dashboard** | Monthly revenue charts, blocked card list, total outstanding dues |

---

## 🚀 Setup Instructions

### 1. Clone & Navigate
```bash
cd mess_system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install django pillow qrcode django-crispy-forms crispy-bootstrap5 django-widget-tweaks whitenoise
```

### 4. Run Migrations
```bash
python manage.py makemigrations accounts meals billing notifications attendance
python manage.py migrate
```

### 5. Seed Demo Data
```bash
python manage.py seed_demo
```

### 6. Start Development Server
```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000**

---

## 👤 Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Mess Staff | `staff1` | `staff123` |
| Student | `stu1` | `stu123` |
| Student | `stu2` | `stu123` |
| Student | `stu3` | `stu123` |

---

## 🏗️ Project Structure

```
mess_system/
├── accounts/           # Users, StudentProfile, SystemConfig
│   ├── models.py       # User, StudentProfile (QR, card status, pending)
│   ├── views.py        # Register, login, dashboards, approve students
│   ├── forms.py        # Registration & login forms
│   └── management/commands/seed_demo.py
├── meals/              # Menu, pricing, scheduling, bookings
│   ├── models.py       # MenuConfig, MealPrice, WeeklySchedule, DailyBooking
│   ├── services.py     # Auto-booking engine, daily override logic
│   └── signals.py      # Menu/price change → schedule invalidation
├── billing/            # Monthly bills, payments, revenue
│   ├── models.py       # MonthlyBill, Payment
│   └── services.py     # Recalculate bills, cancel bookings, broadcasts
├── notifications/      # In-app notification system
│   ├── models.py       # Notification
│   └── services.py     # send_notification(), broadcast_notification()
├── attendance/         # QR scan processing
│   ├── models.py       # AttendanceLog
│   └── views.py        # Camera QR scanner + JSON API
├── templates/          # All HTML templates
│   ├── base.html       # Sidebar layout, alert bars, topbar
│   ├── accounts/       # Login, register, dashboards, QR card
│   ├── meals/          # Weekly schedule, daily override, history, menu mgmt
│   ├── billing/        # Summary, admin billing, revenue chart
│   ├── attendance/     # QR scanner (jsQR camera), report
│   └── notifications/  # Notification list
└── mess_system/        # Django project config
    ├── settings.py
    └── urls.py
```

---

## 🔄 Key Business Logic Flows

### Student Registration
1. Student registers → status = `PENDING`
2. Admin approves → status = `APPROVED` → notification sent
3. Student can now log in and set weekly schedule

### Meal Booking Flow
1. Student sets weekly schedule (veg/nonveg/skip per session per day)
2. System generates `DailyBooking` rows for next 4 weeks
3. Student can override individual days before deadline (default 09:00)
4. At meal time: staff scans QR → system marks `ATTENDED`
5. Missed meals remain billable

### Billing & Card Status
1. Monthly bill = sum of all non-skipped, non-cancelled bookings
2. Pending = total billed − total paid
3. Warning at > 2/3 of limit (₹2000 / ₹3000)
4. Card blocked + future bookings cancelled when pending > limit

### Menu/Price Change
1. Admin saves new MenuConfig or MealPrice
2. Signal fires → all future bookings cancelled
3. All active weekly schedules deactivated
4. Broadcast notification sent to all approved students
5. Students must set a new weekly schedule

---

## ⚙️ Admin Configuration

Visit `/admin/` → **System Configuration** to set:
- `pending_limit` — Amount above which card is blocked (default ₹3000)
- `warning_fraction` — Fraction that triggers warning (default 0.667)
- `booking_deadline_hour` — Cutoff hour for same-day changes (default 9)
