from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import requests
import calendar
from config import Config
from models import db, User, UserSettings, Period, Product, ProductHistory, Medication, MedicationHistory

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Helper functions
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_user_data():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return user
    return None

def calculate_cycle_stats(user_id):
    periods = Period.query.filter_by(user_id=user_id).order_by(Period.start_date.desc()).all()
    
    if len(periods) < 1:
        return {
            'average_length': 28,
            'last_period': None,
            'next_period': None,
            'fertility_window': None,
            'current_day': 1,
            'days_until_next_period': None,
            'days_until_ovulation': None
        }
    
    last_period = periods[0].start_date
    current_day = (datetime.now().date() - last_period).days + 1
    
    if len(periods) < 2:
        avg_length = 28
    else:
        cycle_lengths = []
        for i in range(len(periods) - 1):
            start_current = periods[i].start_date
            start_previous = periods[i+1].start_date
            cycle_length = (start_current - start_previous).days
            cycle_lengths.append(cycle_length)
        
        avg_length = sum(cycle_lengths) // len(cycle_lengths) if cycle_lengths else 28
    
    next_period = last_period + timedelta(days=avg_length)
    ovulation_day = next_period - timedelta(days=14)
    fertility_start = ovulation_day - timedelta(days=5)
    fertility_end = ovulation_day + timedelta(days=1)
    
    days_until_next_period = (next_period - datetime.now().date()).days
    days_until_ovulation = (ovulation_day - datetime.now().date()).days
    
    return {
        'average_length': avg_length,
        'last_period': last_period.strftime('%b %d'),
        'next_period': next_period.strftime('%b %d'),
        'fertility_window': f"{fertility_start.strftime('%b %d')} - {fertility_end.strftime('%b %d')}",
        'current_day': current_day,
        'days_until_next_period': max(0, days_until_next_period),
        'days_until_ovulation': max(0, days_until_ovulation)
    }

def check_for_notifications(user_settings, cycle_stats, upcoming_meds, supplies):
    now = datetime.now()
    
    # Check Cycle Reminders
    if user_settings.get('cycle_reminders', False):
        days_due = cycle_stats.get('days_until_next_period')
        if days_due is not None:
            if days_due == 0:
                flash('Your period is due today.', 'info')
            elif days_due == 1:
                flash('Your period is due tomorrow.', 'info')
            
        days_to_ovulation = cycle_stats.get('days_until_ovulation')
        if days_to_ovulation is not None and 0 <= days_to_ovulation <= 2:
            flash('Your fertility window is open. Ovulation is likely soon.', 'info')

    # Check Medication Reminders
    if user_settings.get('medication_reminders', False) and upcoming_meds:
        first_med = upcoming_meds[0]
        time_diff_seconds = (first_med.next_dose - now).total_seconds()
        
        if 0 < time_diff_seconds <= 1800:
            flash(f"Reminder: Time to take {first_med.name}.", 'warning')
        
        if -1800 < time_diff_seconds <= 0:
             flash(f"You may have missed your dose for {first_med.name}.", 'warning')

    # Check Supply Alerts
    if user_settings.get('supply_alerts', False):
        low_stock_items = [s.name for s in supplies if s.status in ('Running Low', 'Out of Stock')]
        if len(low_stock_items) == 1:
            flash(f"You are running low on {low_stock_items[0]}.", 'danger')
        elif len(low_stock_items) > 1:
            flash(f"You are running low on {len(low_stock_items)} items.", 'danger')

@app.context_processor
def inject_user_settings():
    if 'user_id' in session:
        user = get_user_data()
        if user and user.settings:
            return dict(user_settings={
                'cycle_reminders': user.settings.cycle_reminders,
                'medication_reminders': user.settings.medication_reminders,
                'supply_alerts': user.settings.supply_alerts,
                'notification_sounds': user.settings.notification_sounds,
                'passcode_lock': user.settings.passcode_lock
            })
    
    return dict(user_settings={
        'cycle_reminders': False,
        'medication_reminders': False,
        'supply_alerts': False,
        'notification_sounds': False,
        'passcode_lock': False
    })

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    today = datetime.now()
    return render_template('index.html', today=today)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('full-name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create default settings
        settings = UserSettings(
            user_id=user.id,
            cycle_reminders=True,
            medication_reminders=True,
            supply_alerts=False,
            notification_sounds=True,
            passcode_lock=False
        )
        db.session.add(settings)
        db.session.commit()
        
        session['user_id'] = user.id
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_data()
    cycle_stats = calculate_cycle_stats(user.id)
    
    # Get current hour to determine greeting
    now = datetime.now()
    hour = now.hour
    
    if hour < 12:
        greeting = "Good morning"
    elif hour < 16:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Calendar data
    today = datetime.now()
    first_day_of_month = today.replace(day=1)
    start_day_offset = (first_day_of_month.weekday() + 1) % 7 
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    # Get upcoming medications
    upcoming_meds = Medication.query.filter(
        Medication.user_id == user.id,
        Medication.next_dose >= now - timedelta(minutes=30)
    ).order_by(Medication.next_dose).limit(3).all()
    
    # Format medication times
    for med in upcoming_meds:
        time_diff = med.next_dose - now
        if time_diff.total_seconds() < 0:
            med.time_until = "Due now"
        else:
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            med.time_until = f"{hours} hours {minutes} minutes"
    
    # Get supplies with stock status
    supplies = Product.query.filter_by(user_id=user.id).all()
    for supply in supplies:
        initial_qty = supply.initial_quantity if supply.initial_quantity > 0 else 1
        
        if supply.quantity <= 0:
            supply.status = 'Out of Stock'
            supply.status_class = 'status-error'
        elif supply.quantity < (initial_qty * 0.25):
            supply.status = 'Running Low'
            supply.status_class = 'status-warning'
        else:
            supply.status = 'Stocked'
            supply.status_class = 'status-success'
            
    # Get settings
    user_settings = {
        'cycle_reminders': user.settings.cycle_reminders if user.settings else True,
        'medication_reminders': user.settings.medication_reminders if user.settings else True,
        'supply_alerts': user.settings.supply_alerts if user.settings else False,
        'notification_sounds': user.settings.notification_sounds if user.settings else True
    }
    
    check_for_notifications(user_settings, cycle_stats, upcoming_meds, supplies)
    
    return render_template('dashboard.html', 
                           user=user, 
                           cycle_stats=cycle_stats,
                           upcoming_meds=upcoming_meds,
                           supplies=supplies,
                           greeting=greeting,
                           today=today,
                           month_calendar_data={
                               'start_day_offset': start_day_offset,
                               'days_in_month': days_in_month
                           })

@app.route('/period')
@login_required
def period():
    user = get_user_data()
    cycle_stats = calculate_cycle_stats(user.id)
    
    # Get period history
    periods = Period.query.filter_by(user_id=user.id).order_by(Period.start_date.desc()).all()
    
    return render_template('period.html', 
                           user=user, 
                           cycle_stats=cycle_stats,
                           periods=periods)

@app.route('/add_period', methods=['POST'])
@login_required
def add_period():
    start_date = datetime.strptime(request.form.get('start-date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end-date'), '%Y-%m-%d').date()
    notes = request.form.get('notes', '')
    
    period = Period(
        user_id=session['user_id'],
        start_date=start_date,
        end_date=end_date,
        notes=notes
    )
    db.session.add(period)
    db.session.commit()
    
    flash('Period added successfully!', 'success')
    return redirect(url_for('period'))

@app.route('/update_period/<int:period_id>', methods=['POST'])
@login_required
def update_period(period_id):
    period = Period.query.filter_by(id=period_id, user_id=session['user_id']).first()
    if not period:
        flash('Period not found', 'danger')
        return redirect(url_for('period'))
    
    period.start_date = datetime.strptime(request.form.get('start-date'), '%Y-%m-%d').date()
    period.end_date = datetime.strptime(request.form.get('end-date'), '%Y-%m-%d').date()
    period.notes = request.form.get('notes', '')
    
    db.session.commit()
    flash('Period updated successfully!', 'success')
    return redirect(url_for('period'))

@app.route('/delete_period/<int:period_id>', methods=['POST'])
@login_required
def delete_period(period_id):
    period = Period.query.filter_by(id=period_id, user_id=session['user_id']).first()
    if period:
        db.session.delete(period)
        db.session.commit()
        flash('Period deleted successfully!', 'success')
    else:
        flash('Period not found', 'danger')
    return redirect(url_for('period'))

@app.route('/products')
@login_required
def products():
    user = get_user_data()
    
    # Get products
    products = Product.query.filter_by(user_id=user.id).all()
    
    # Get product history
    history = ProductHistory.query.filter_by(user_id=user.id).order_by(ProductHistory.date.desc()).all()
    
    # Group history by date
    grouped_history = {}
    for item in history:
        date_str = item.date.strftime('%B %d, %Y')
        if date_str not in grouped_history:
            grouped_history[date_str] = []
        grouped_history[date_str].append(item)
    
    return render_template('products.html', 
                           user=user, 
                           products=products,
                           grouped_history=grouped_history)

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    quantity = int(request.form.get('quantity'))
    
    product = Product(
        user_id=session['user_id'],
        name=name,
        category=category,
        quantity=quantity,
        initial_quantity=quantity
    )
    db.session.add(product)
    db.session.commit()
    
    flash('Product added successfully!', 'success')
    return redirect(url_for('products'))

@app.route('/update_product/<int:product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=session['user_id']).first()
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('products'))
    
    product.name = request.form.get('name')
    product.category = request.form.get('category')
    quantity = int(request.form.get('quantity'))
    product.quantity = quantity
    product.initial_quantity = quantity
    
    db.session.commit()
    flash('Product updated successfully!', 'success')
    return redirect(url_for('products'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=session['user_id']).first()
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    else:
        flash('Product not found', 'danger')
    return redirect(url_for('products'))

@app.route('/use_product/<int:product_id>', methods=['POST'])
@login_required
def use_product(product_id):
    source = request.form.get('source', 'products')
    
    product = Product.query.filter_by(id=product_id, user_id=session['user_id']).first()
    
    if product and product.quantity > 0:
        # Update quantity
        product.quantity -= 1
        db.session.commit()
        
        # Add to history
        history = ProductHistory(
            user_id=session['user_id'],
            product_id=product_id,
            product_name=product.name
        )
        db.session.add(history)
        db.session.commit()
        
        try:
            requests.get(f"http://{app.config['NODEMCU_IP']}/trigger/supply", timeout=0.5)
            print("Triggered supply LED")
        except requests.RequestException as e:
            print(f"Warning: Could not connect to NodeMCU for supply. {e}")
        
        flash(f'Used 1 {product.name}', 'success')
    else:
        flash('Product out of stock', 'danger')
    
    if source == 'dashboard':
        return redirect(url_for('dashboard'))
    return redirect(url_for('products'))

@app.route('/medications')
@login_required
def medications():
    user = get_user_data()
    
    # Get medications
    medications = Medication.query.filter_by(user_id=user.id).all()
    
    # Get medication history
    history = MedicationHistory.query.filter_by(user_id=user.id).order_by(MedicationHistory.date.desc()).all()
    
    # Group history by date
    grouped_history = {}
    for item in history:
        date_str = item.date.strftime('%B %d, %Y')
        if date_str not in grouped_history:
            grouped_history[date_str] = []
        grouped_history[date_str].append(item)
    
    # Group medications by time of day
    morning_meds = [m for m in medications if m.time_of_day == 'morning']
    evening_meds = [m for m in medications if m.time_of_day == 'evening']
    
    return render_template('medications.html', 
                           user=user, 
                           medications=medications,
                           morning_meds=morning_meds,
                           evening_meds=evening_meds,
                           grouped_history=grouped_history)

@app.route('/add_medication', methods=['POST'])
@login_required
def add_medication():
    name = request.form.get('name')
    dosage = request.form.get('dosage')
    frequency = request.form.get('frequency')
    time_of_day = request.form.get('time_of_day')
    quantity = int(request.form.get('quantity'))
    
    # Calculate next dose based on frequency
    now = datetime.now()
    if frequency == 'daily':
        if time_of_day == 'morning':
            next_dose = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if next_dose < now:
                next_dose += timedelta(days=1)
        else:
            next_dose = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if next_dose < now:
                next_dose += timedelta(days=1)
    elif frequency == 'weekly':
        next_dose = now + timedelta(days=7)
    elif frequency == 'monthly':
        next_dose = now + timedelta(days=30)
    else:
        next_dose = now
    
    medication = Medication(
        user_id=session['user_id'],
        name=name,
        dosage=dosage,
        frequency=frequency,
        time_of_day=time_of_day,
        quantity=quantity,
        initial_quantity=quantity,
        next_dose=next_dose
    )
    db.session.add(medication)
    db.session.commit()
    
    flash('Medication added successfully!', 'success')
    return redirect(url_for('medications'))

@app.route('/update_medication/<int:med_id>', methods=['POST'])
@login_required
def update_medication(med_id):
    medication = Medication.query.filter_by(id=med_id, user_id=session['user_id']).first()
    if not medication:
        flash('Medication not found', 'danger')
        return redirect(url_for('medications'))
    
    medication.name = request.form.get('name')
    medication.dosage = request.form.get('dosage')
    medication.frequency = request.form.get('frequency')
    medication.time_of_day = request.form.get('time_of_day')
    quantity = int(request.form.get('quantity'))
    medication.quantity = quantity
    medication.initial_quantity = quantity
    
    # Calculate next dose based on frequency
    now = datetime.now()
    if medication.frequency == 'daily':
        if medication.time_of_day == 'morning':
            next_dose = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if next_dose < now:
                next_dose += timedelta(days=1)
        else:
            next_dose = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if next_dose < now:
                next_dose += timedelta(days=1)
    elif medication.frequency == 'weekly':
        next_dose = now + timedelta(days=7)
    elif medication.frequency == 'monthly':
        next_dose = now + timedelta(days=30)
    else:
        next_dose = now
    
    medication.next_dose = next_dose
    db.session.commit()
    
    flash('Medication updated successfully!', 'success')
    return redirect(url_for('medications'))

@app.route('/delete_medication/<int:med_id>', methods=['POST'])
@login_required
def delete_medication(med_id):
    medication = Medication.query.filter_by(id=med_id, user_id=session['user_id']).first()
    if medication:
        db.session.delete(medication)
        db.session.commit()
        flash('Medication deleted successfully!', 'success')
    else:
        flash('Medication not found', 'danger')
    return redirect(url_for('medications'))

@app.route('/take_medication/<int:med_id>', methods=['POST'])
@login_required
def take_medication(med_id):
    source = request.form.get('source', 'medications')
    
    medication = Medication.query.filter_by(id=med_id, user_id=session['user_id']).first()
    
    if medication and medication.quantity > 0:
        # Update quantity
        medication.quantity -= 1
        
        # Calculate next dose
        now = datetime.now()
        if medication.frequency == 'daily':
            if medication.time_of_day == 'morning':
                next_dose = now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_dose = now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif medication.frequency == 'weekly':
            next_dose = now + timedelta(days=7)
        elif medication.frequency == 'monthly':
            next_dose = now + timedelta(days=30)
        else:
            next_dose = now
        
        medication.next_dose = next_dose
        
        # Add to history
        history = MedicationHistory(
            user_id=session['user_id'],
            medication_id=med_id,
            medication_name=medication.name,
            dosage=medication.dosage
        )
        db.session.add(history)
        db.session.commit()
        
        try:
            requests.get(f"http://{app.config['NODEMCU_IP']}/trigger/medication", timeout=0.5)
            print("Triggered medication LED")
        except requests.RequestException as e:
            print(f"Warning: Could not connect to NodeMCU for medication. {e}")
        
        flash(f'Took {medication.dosage} of {medication.name}', 'success')
    else:
        flash('Medication out of stock', 'danger')
    
    if source == 'dashboard':
        return redirect(url_for('dashboard'))
    return redirect(url_for('medications'))

@app.route('/profile')
@login_required
def profile():
    user = get_user_data()
    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('profile'))
    
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('profile'))
    
    if not user.settings:
        user.settings = UserSettings(user_id=user.id)
    
    user.settings.cycle_reminders = 'cycle_reminders' in request.form
    user.settings.medication_reminders = 'medication_reminders' in request.form
    user.settings.supply_alerts = 'supply_alerts' in request.form
    user.settings.notification_sounds = 'notification_sounds' in request.form
    user.settings.passcode_lock = 'passcode_lock' in request.form
    
    db.session.commit()
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('profile'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)