from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db: SQLAlchemy = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Added admin role
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship("Reservation", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.name}>"


class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    total_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    spots = db.relationship(
        "ParkingSpot", backref="lot", cascade="all, delete-orphan", lazy=True
    )

    def available_spots_count(self):
        return len([spot for spot in self.spots if not spot.is_occupied])

    def __repr__(self):
        return f"<ParkingLot {self.name}>"


class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.String(10), nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    lot_id = db.Column(db.Integer, db.ForeignKey("parking_lot.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Remove circular dependency - we'll get current reservation through query
    reservations = db.relationship("Reservation", backref="spot", lazy=True)

    def get_current_reservation(self):
        return Reservation.query.filter_by(spot_id=self.id, checkout_time=None).first()

    def __repr__(self):
        return f"<ParkingSpot {self.spot_number}>"


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey("parking_spot.id"), nullable=False)

    vehicle_number = db.Column(db.String(20), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    checkout_time = db.Column(db.DateTime, nullable=True)

    # Calculate duration and cost
    def duration_hours(self):
        if self.checkout_time:
            duration = self.checkout_time - self.checkin_time
            return round(duration.total_seconds() / 3600, 2)
        else:
            duration = datetime.utcnow() - self.checkin_time
            return round(duration.total_seconds() / 3600, 2)

    def calculate_cost(self, rate_per_hour=5):
        return round(self.duration_hours() * rate_per_hour, 2)

    def __repr__(self):
        return f"<Reservation {self.vehicle_number}>"
