from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, ParkingLotForm, ReservationForm
from models import db, User, ParkingLot, ParkingSpot, Reservation
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '#123abc!@#'

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'parking.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create database directory
os.makedirs('database', exist_ok=True)

# Initialize database
db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def create_tables_and_admin():
    db.create_all()

    admin = User.query.filter_by(email='admin@parking.com').first()
    if not admin:
        admin_user = User(
            name='Admin User',
            address='Admin Address',
            phone='1234567890',
            email='admin@parking.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin created: admin@parking.com / admin123")

# HOME ROUTES
@app.route('/')
def home():
    user_name = session.get('user_name')
    is_admin = session.get('is_admin', False)

    # Get some stats for the home page
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(is_occupied=True).count()
    available_spots = total_spots - occupied_spots

    return render_template('home.html',
                         user_name=user_name,
                         is_admin=is_admin,
                         total_lots=total_lots,
                         total_spots=total_spots,
                         occupied_spots=occupied_spots,
                         available_spots=available_spots)

# AUTH ROUTES
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Check if email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please login instead.', 'danger')
            return redirect(url_for('login'))

        # Create new user
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            name=form.name.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin

            flash(f'Welcome back, {user.name}!', 'success')

            # Redirect admin to admin dashboard
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

# USER ROUTES
@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve_spot():
    form = ReservationForm()

    # Check if user already has an active reservation
    existing_reservation = Reservation.query.filter_by(
        user_id=session['user_id'],
        checkout_time=None
    ).first()

    if existing_reservation:
        flash('You already have an active reservation. Please check out first.', 'warning')
        return redirect(url_for('my_reservation'))

    # Populate lot choices
    lots = ParkingLot.query.all()
    form.lot_id.choices = [(lot.id, f"{lot.name} - {lot.location}") for lot in lots]

    if not lots:
        flash('No parking lots available. Please contact admin.', 'warning')
        return redirect(url_for('home'))

    # Handle lot selection for spot loading
    selected_lot_id = None
    if request.method == 'POST':
        selected_lot_id = form.lot_id.data
    elif lots:
        selected_lot_id = lots[0].id

    # Populate spot choices based on selected lot
    if selected_lot_id:
        available_spots = ParkingSpot.query.filter_by(
            lot_id=selected_lot_id,
            is_occupied=False
        ).all()
        form.spot_id.choices = [(spot.id, spot.spot_number) for spot in available_spots]

        if not available_spots:
            flash('No available spots in the selected parking lot.', 'warning')

    if form.validate_on_submit():
        # Create reservation
        reservation = Reservation(
            user_id=session['user_id'],
            spot_id=form.spot_id.data,
            vehicle_number=form.vehicle_number.data.upper()
        )

        # Update spot status
        spot = ParkingSpot.query.get(form.spot_id.data)
        spot.is_occupied = True

        db.session.add(reservation)
        db.session.commit()

        flash('Parking spot reserved successfully!', 'success')
        return redirect(url_for('my_reservation'))

    return render_template('reserve.html', form=form, lots=lots)

@app.route('/get_spots/<int:lot_id>')
@login_required
def get_spots(lot_id):
    """AJAX endpoint to get available spots for a parking lot"""
    spots = ParkingSpot.query.filter_by(lot_id=lot_id, is_occupied=False).all()
    spots_data = [{'id': spot.id, 'number': spot.spot_number} for spot in spots]
    return jsonify(spots_data)

@app.route('/my-reservation')
@login_required
def my_reservation():
    reservation = Reservation.query.filter_by(
        user_id=session['user_id'],
        checkout_time=None
    ).first()

    return render_template('my_reservation.html', reservation=reservation)

@app.route('/checkout/<int:reservation_id>', methods=['POST'])
@login_required
def checkout(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    # Check if reservation belongs to current user
    if reservation.user_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('home'))

    # Update reservation and spot
    reservation.checkout_time = datetime.utcnow()
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.is_occupied = False

    db.session.commit()

    duration = reservation.duration_hours()
    cost = reservation.calculate_cost()

    flash(f'Checked out successfully! Duration: {duration} hours, Cost: ${cost}', 'success')
    return redirect(url_for('reservation_history'))

@app.route('/reservation-history')
@login_required
def reservation_history():
    reservations = Reservation.query.filter_by(user_id=session['user_id']).order_by(
        Reservation.checkin_time.desc()
    ).all()

    return render_template('reservation_history.html', reservations=reservations)

# ADMIN ROUTES
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get statistics
    total_users = User.query.filter_by(is_admin=False).count()
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(is_occupied=True).count()
    active_reservations = Reservation.query.filter_by(checkout_time=None).count()

    # Recent reservations
    recent_reservations = Reservation.query.order_by(
        Reservation.checkin_time.desc()
    ).limit(10).all()

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_lots=total_lots,
                         total_spots=total_spots,
                         occupied_spots=occupied_spots,
                         available_spots=total_spots - occupied_spots,
                         active_reservations=active_reservations,
                         recent_reservations=recent_reservations)

@app.route('/admin/add-lot', methods=['GET', 'POST'])
@admin_required
def add_lot():
    form = ParkingLotForm()

    if form.validate_on_submit():
        # Create parking lot
        lot = ParkingLot(
            name=form.name.data,
            location=form.location.data,
            total_spots=form.total_spots.data
        )

        db.session.add(lot)
        db.session.flush()  # Get the lot ID

        # Create parking spots
        for i in range(1, lot.total_spots + 1):
            spot = ParkingSpot(
                spot_number=f"{lot.name[:3].upper()}-{i:03d}",
                lot_id=lot.id
            )
            db.session.add(spot)

        db.session.commit()

        flash(f'Parking lot "{lot.name}" with {lot.total_spots} spots added successfully!', 'success')
        return redirect(url_for('manage_lots'))

    return render_template('admin/add_lot.html', form=form)

@app.route('/admin/edit-lot/<int:lot_id>', methods=['GET', 'POST'])
@admin_required
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = ParkingLotForm(obj=lot)

    if form.validate_on_submit():
        lot.name = form.name.data
        lot.location = form.location.data

        # If total_spots is increased, add new spots
        if form.total_spots.data > lot.total_spots:
            current_count = lot.total_spots
            for i in range(current_count + 1, form.total_spots.data + 1):
                spot = ParkingSpot(
                    spot_number=f"{lot.name[:3].upper()}-{i:03d}",
                    lot_id=lot.id
                )
                db.session.add(spot)
        lot.total_spots = form.total_spots.data

        db.session.commit()
        flash('Parking lot updated successfully.', 'success')
        return redirect(url_for('manage_lots'))

    return render_template('admin/edit_lot.html', form=form, lot=lot)

@app.route('/admin/lots')
@admin_required
def manage_lots():
    lots = ParkingLot.query.all()
    return render_template('admin/manage_lots.html', lots=lots)

@app.route('/admin/lot/<int:lot_id>')
@admin_required
def view_lot_details(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()

    return render_template('admin/view_lot_details.html', lot=lot, spots=spots)

@app.route('/admin/reservations')
@admin_required
def manage_reservations():
    page = request.args.get('page', 1, type=int)
    reservations = Reservation.query.order_by(
        Reservation.checkin_time.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    return render_template('admin/manage_reservations.html', reservations=reservations)

@app.route('/admin/reservation/<int:res_id>/cancel')
@admin_required
def cancel_reservation(res_id):
    reservation = Reservation.query.get_or_404(res_id)

    if reservation.checkout_time is None:
        reservation.checkout_time = datetime.utcnow()
        reservation.spot.is_occupied = False
        db.session.commit()
        flash("Reservation successfully cancelled.", "success")
    else:
        flash("Reservation is already inactive.", "warning")

    return redirect(url_for('manage_reservations'))

@app.route('/admin/users')
@admin_required
def manage_users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/user/<int:user_id>/delete')
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash("Cannot delete admin users.", "warning")
        return redirect(url_for('manage_users'))

    # Delete associated reservations
    Reservation.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully.", "success")
    return redirect(url_for('manage_users'))

@app.route('/admin/delete-lot/<int:lot_id>', methods=['POST'])
@admin_required
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # Check if any spots are currently occupied
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot_id, is_occupied=True).count()
    if occupied_spots > 0:
        flash(f'Cannot delete lot "{lot.name}" - {occupied_spots} spots are currently occupied.', 'danger')
        return redirect(url_for('manage_lots'))

    db.session.delete(lot)
    db.session.commit()

    flash(f'Parking lot "{lot.name}" deleted successfully.', 'success')
    return redirect(url_for('manage_lots'))

# ERROR HANDLERS
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        create_tables_and_admin()
    app.run(debug=False)
