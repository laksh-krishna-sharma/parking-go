from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    IntegerField,
    SelectField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Regexp


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField("Address", validators=[DataRequired(), Length(max=200)])
    phone = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Length(10, 15),
            Regexp(r"^\+?[0-9\s\-\(\)]+$", message="Invalid phone number format"),
        ],
    )
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class ParkingLotForm(FlaskForm):
    name = StringField("Parking Lot Name", validators=[DataRequired(), Length(max=150)])
    location = StringField("Location", validators=[DataRequired(), Length(max=200)])
    total_spots = IntegerField(
        "Total Spots", validators=[DataRequired(), NumberRange(min=1, max=1000)]
    )
    submit = SubmitField("Add Parking Lot")


class ReservationForm(FlaskForm):
    lot_id = SelectField("Select Parking Lot", coerce=int, validators=[DataRequired()])
    spot_id = SelectField(
        "Select Parking Spot", coerce=int, validators=[DataRequired()]
    )
    vehicle_number = StringField(
        "Vehicle Number",
        validators=[
            DataRequired(),
            Length(max=20),
            Regexp(
                r"^[A-Z0-9\-\s]+$",
                message="Vehicle number should contain only letters, numbers, hyphens and spaces",
            ),
        ],
    )
    submit = SubmitField("Book Parking Spot")
