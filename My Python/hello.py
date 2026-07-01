from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Initialize live OpenAI Client using your API key
client = OpenAI(api_key="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")

# Configure Tesseract path (Windows default install)
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# File paths
DATA_FILE = os.path.join("data", "students.xlsx")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load student data safely
if os.path.exists(DATA_FILE):
    students_df = pd.read_excel(DATA_FILE)
    students_df["Student Name"] = students_df["Student Name"].astype(str).str.strip().str.upper()
    if "Certificate ID" in students_df.columns:
        students_df["Certificate ID"] = students_df["Certificate ID"].astype(str).str.strip().str.upper()
else:
    students_df = pd.DataFrame(columns=["Student Name", "Certificate ID"])

users = {}  # In-memory temporary user database

@app.route("/")
def home():
    return redirect(url_for("register"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please fill all fields!", "danger")
            return redirect(url_for("register"))

        if username in users:
            flash("Username already exists!", "warning")
            return redirect(url_for("register"))
        
        users[username] = password
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username in users and users[username] == password:
            session["user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
        
    # Initialize isolated, user-specific stacks in session if missing
    if "results_list" not in session:
        session["results_list"] = []
    if "history_list" not in session:
        session["history_list"] = []
    
    if request.method == "POST":
        verification_method = request.form.get("verification_method")
        result = {}
        
        # Pull history list specifically from this user's browser session
        user_history = session["history_list"]
        
        # --- METHOD A: MANUAL TEXT ENTRY VERIFICATION ---
        if verification_method == "manual":
            input_name = request.form.get("student_name", "").strip().upper()
            input_id = request.form.get("certificate_id", "").strip().upper()
            
            user_history.append({
                "user": session['user'],
                "file": f"Manual Check ({input_name})",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            if "Certificate ID" in students_df.columns:
                match = students_df[
                    (students_df["Student Name"] == input_name) & 
                    (students_df["Certificate ID"] == input_id)
                ]
            else:
                match = students_df[students_df["Student Name"] == input_name]
                
            if not match.empty:
                result = match.to_dict(orient="records")[0]
                result["StudentName_Extracted"] = input_name
                result["status"] = "Verified"
            else:
                result = {
                    "Error": "No exact matching record found for this Name and ID combination.",
                    "status": "Failed"
                }
                
            result["File_Processed"] = f"Manual Verification Matrix (ID: {input_id})"
            result["Timestamp"] = datetime.now().strftime("%H:%M:%S")

        # --- METHOD B: AUTOMATED PDF FILE UPLOAD ---
        else:
            file = request.files.get("certificate")
            if file and file.filename != '':
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                
                user_history.append({
                    "user": session['user'],
                    "file": file.filename,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                try:
                    reader = PdfReader(filepath)
                    text = "".join([page.extract_text() or "" for page in reader.pages])
                    
                    if not text.strip():
                        images = convert_from_path(filepath)
                        text = "".join([pytesseract.image_to_string(img) for img in images])
                    
                    student_name = None
                    text_upper = text.upper()
                    for name in students_df["Student Name"].unique():
                        if name in text_upper:
                            student_name = name
                            break
                    
                    if student_name:
                        match = students_df[students_df["Student Name"] == student_name]
                        if not match.empty:
                            result = match.to_dict(orient="records")[0]
                            result["StudentName_Extracted"] = student_name
                            result["status"] = "Verified"
                        else:
                            result = {"Error": "Name detected but missing from database registries.", "StudentName_Extracted": student_name, "status": "Failed"}
                    else:
                        result = {"Error": "No registered student identification string found inside certificate text layout.", "status": "Failed"}
                except Exception as e:
                    result = {"Error": f"Internal compilation failure: {str(e)}", "status": "Error"}
                
                result["File_Processed"] = file.filename
                result["Timestamp"] = datetime.now().strftime("%H:%M:%S")
        
        # Save structural changes back to session store
        session["history_list"] = user_history
        if result:
            # Force user execution identity context
            result["user"] = session["user"]
            
            current_list = session["results_list"]
            current_list.insert(0, result)
            session["results_list"] = current_list
            
        session.modified = True
        flash("Verification processing executed successfully.", "success")
        return render_template("dashboard.html", user=session["user"], history=session["history_list"], results=session["results_list"], active_tab="verify")
            
    return render_template("dashboard.html", user=session["user"], history=session["history_list"], results=session["results_list"], active_tab="upload")

@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    
    if not user_message:
        return jsonify({"reply": "I didn't catch that. Could you please rephrase?"})

    try:
        # Define the AI's identity context and system knowledge parameters
        system_instructions = (
            "You are the expert AI Co-Pilot assistant for the Verify Engine Workspace Terminal. "
            "Your job is to guide users politely on how to navigate and use this specific web application.\n\n"
            "Here is the documentation on how the app works:\n"
            "1. 'Check Certificate' Tab: Contains two options to verify student credentials against an Excel database.\n"
            "   - 'Upload Document File': Users drop or click to upload a PDF certificate layout. The system extracts text using PyPDF2/Tesseract OCR.\n"
            "   - 'Enter Details Manually': Users type the Student's Full Name (e.g. JOHN DOE) and Certificate Serial ID Number.\n"
            "2. 'Live Verification' Tab: Shows a dynamic Results Matrix of checking cards processed during the current session.\n"
            "3. 'Operations History' Tab: Contains private system log tables. Every user's history is isolated securely.\n\n"
            "Rules:\n"
            "- Always answer short, concise, friendly, and professional.\n"
            "- You can use basic HTML formatting like <b>, <i>, or <br> to make your instructions look elegant in the chat bubble."
        )

        # Call the live OpenAI Chat Completions endpoint
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5
        )
        
        # Extract response text layout
        bot_reply = response.choices[0].message.content
        
    except Exception as e:
        bot_reply = f"🤖 AI Service Interruption: Unable to contact engine. Details: {str(e)}"

    return jsonify({"reply": bot_reply})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)