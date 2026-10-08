from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-later"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(150), nullable=False)
    job_link = db.Column(db.String(300))
    source = db.Column(db.String(50))
    status = db.Column(db.String(30), default="Applied")
    applied_date = db.Column(db.Date, default=date.today)
    follow_up_date = db.Column(db.Date)
    notes = db.Column(db.Text)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or len(password) < 6:
            flash("Fill all fields. Password needs at least 6 characters.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("This email is already registered.")
            return redirect(url_for("register"))

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Wrong email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    applications = (
        Application.query.filter_by(user_id=current_user.id)
        .order_by(Application.applied_date.desc())
        .all()
    )
    return render_template("dashboard.html", applications=applications)


@app.route("/applications/add", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        company = request.form["company"].strip()
        role = request.form["role"].strip()
        if not company or not role:
            flash("Company and role are required.")
            return redirect(url_for("add_application"))

        follow_up = request.form.get("follow_up_date")
        application = Application(
            user_id=current_user.id,
            company=company,
            role=role,
            job_link=request.form.get("job_link", "").strip(),
            source=request.form.get("source", "").strip(),
            status=request.form.get("status", "Applied"),
            follow_up_date=date.fromisoformat(follow_up) if follow_up else None,
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(application)
        db.session.commit()
        flash("Application added!")
        return redirect(url_for("dashboard"))

    return render_template("add_application.html")


@app.route("/applications/<int:app_id>/edit", methods=["GET", "POST"])
@login_required
def edit_application(app_id):
    application = db.session.get(Application, app_id)
    if application is None or application.user_id != current_user.id:
        abort(404)

    if request.method == "POST":
        company = request.form["company"].strip()
        role = request.form["role"].strip()
        if not company or not role:
            flash("Company and role are required.")
            return redirect(url_for("edit_application", app_id=app_id))

        follow_up = request.form.get("follow_up_date")
        application.company = company
        application.role = role
        application.job_link = request.form.get("job_link", "").strip()
        application.source = request.form.get("source", "").strip()
        application.status = request.form.get("status", "Applied")
        application.follow_up_date = (
            date.fromisoformat(follow_up) if follow_up else None
        )
        application.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Application updated!")
        return redirect(url_for("dashboard"))

    return render_template("edit_application.html", application=application)


@app.route("/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    application = db.session.get(Application, app_id)
    if application is None or application.user_id != current_user.id:
        abort(404)

    db.session.delete(application)
    db.session.commit()
    flash("Application deleted.")
    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("login"))





if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)