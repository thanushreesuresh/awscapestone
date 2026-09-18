import os
import re
from flask import Flask, render_template, render_template_string, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file size

# Success response template for frontend verification stage
SUCCESS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Received</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <main class="page-container">
        <section class="registration-card" aria-labelledby="confirmation-title">
            <header class="card-header">
                <div class="badge" style="background-color: #ecfdf5; color: #059669;">Backend Verified</div>
                <h1 id="confirmation-title">Registration Received</h1>
                <p class="description">
                    Flask backend successfully received and validated the student submission.
                </p>
            </header>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: 0.85rem;">
                <div>
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Student Name</span>
                    <p style="font-size: 1rem; font-weight: 600; color: #0f172a; margin-top: 0.2rem;">{{ name }}</p>
                </div>
                <div>
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Email Address</span>
                    <p style="font-size: 1rem; font-weight: 600; color: #0f172a; margin-top: 0.2rem;">{{ email }}</p>
                </div>
                <div>
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Enrolled Course</span>
                    <p style="font-size: 1rem; font-weight: 600; color: #0f172a; margin-top: 0.2rem;">{{ course }}</p>
                </div>
                <div>
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Photo Filename</span>
                    <p style="font-size: 1rem; font-weight: 600; color: #0f172a; margin-top: 0.2rem;">{{ filename }}</p>
                </div>
            </div>

            <div style="padding: 0.85rem 1rem; background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px; margin-bottom: 1.5rem; font-size: 0.875rem; color: #1e40af; line-height: 1.4;">
                <strong>Notice:</strong> This is a temporary verification step. Database (MySQL / RDS) and photo storage (Amazon S3) will be integrated in future phases.
            </div>

            <a href="/" class="submit-btn" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                Register Another Student
            </a>
        </section>
    </main>
</body>
</html>
"""

# Error response template for invalid form submission
ERROR_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Error</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <main class="page-container">
        <section class="registration-card" aria-labelledby="error-title">
            <header class="card-header">
                <div class="badge" style="background-color: #fef2f2; color: #dc2626;">Validation Error</div>
                <h1 id="error-title">Submission Failed</h1>
                <p class="description">
                    The registration request could not be processed due to the following errors:
                </p>
            </header>

            <div style="background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
                <ul style="margin-left: 1.25rem; color: #991b1b; font-size: 0.9375rem; line-height: 1.6;">
                    {% for error in errors %}
                        <li>{{ error }}</li>
                    {% endfor %}
                </ul>
            </div>

            <a href="/" class="submit-btn" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                Back to Registration Form
            </a>
        </section>
    </main>
</body>
</html>
"""

def allowed_file(filename):
    """Check if the uploaded file has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_email(email):
    """Basic email format validation."""
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email.strip()))

@app.route('/')
def index():
    """Renders the Student Registration frontend form."""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """
    Receives and validates the submitted student registration form.
    Validates name, email, course, and photo upload without persisting to database or S3.
    """
    errors = []

    # 1. Retrieve form fields
    name = request.form.get('name')
    email = request.form.get('email')
    course = request.form.get('course')

    # 2. Retrieve uploaded file
    photo = request.files.get('photo')

    # 3. Validate Student Name
    if not name or not name.strip():
        errors.append("Student Name is required.")

    # 4. Validate Email Address
    if not email or not email.strip():
        errors.append("Email Address is required.")
    elif not is_valid_email(email):
        errors.append("A valid email address is required (e.g., student@example.com).")

    # 5. Validate Course
    if not course or not course.strip():
        errors.append("Course selection is required.")

    # 6. Validate Photo Upload
    if not photo or photo.filename.strip() == '':
        errors.append("Student Photo is required.")
    elif not allowed_file(photo.filename):
        errors.append("Photo must be a valid image file (JPG, JPEG, PNG, WEBP, or GIF).")

    # If any validation errors exist, return 400 Bad Request with details
    if errors:
        return render_template_string(ERROR_TEMPLATE, errors=errors), 400

    # Sanitize the filename for safe display
    safe_filename = secure_filename(photo.filename)

    # Temporary success confirmation (no persistence to MySQL or S3 in this stage)
    return render_template_string(
        SUCCESS_TEMPLATE,
        name=name.strip(),
        email=email.strip(),
        course=course.strip(),
        filename=safe_filename
    ), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
