from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "secret_key"  # Needed for sessions

# Allowed upload folder
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Sample Certificates Database (from your PDF)
certificates = {
    "CERTO08": {"student": "Bhargavi Kambli", "course": "B.Tech ECE", "issue_date": "2025-06-15", "student_id": "108"},
    "CERTO18": {"student": "Vaishnavi Mehatri", "course": "B.Tech ECE", "issue_date": "2025-06-15", "student_id": "118"},
    "CERTO04": {"student": "Neha Pawar", "course": "B.Sc Electronics", "issue_date": "2017-10-26", "student_id": "104"},
    "CERT001": {"student": "Vanshika Foshi", "course": "B.Tech ECE", "issue_date": "2025-06-15", "student_id": "101"},
    "CERTO69": {"student": "Riya Patel", "course": "MBBS", "issue_date": "2021-07-17", "student_id": "169"}
}

# ---------------- ROUTES ---------------- #

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form.get("username")
    password = request.form.get("password")
    # Simple check (replace with real auth)
    if username == "admin" and password == "password":
        session["user"] = username
        return redirect(url_for("details"))
    else:
        flash("Invalid credentials!")
        return redirect(url_for("login"))

@app.route('/details')
def details():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("details.html")

@app.route('/upload', methods=['POST'])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    student_id = request.form.get("student_id")
    cert_id = request.form.get("cert_id")
    file = request.files["certificate"]

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

    # Verification logic
    if cert_id in certificates and certificates[cert_id]["student_id"] == student_id:
        cert = certificates[cert_id]
        return render_template("result.html", found=True, cert=cert)
    else:
        return render_template("result.html", found=False)

if __name__ == "__main__":
    app.run(debug=True)
    