import os
import re
import uuid
import boto3
import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, request
from werkzeug.utils import secure_filename

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------
# Database Configuration (Local MySQL)
# ---------------------------------------------------------
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'studentdb')

# ---------------------------------------------------------
# AWS S3 Configuration
# Uses default credential provider chain (IAM role, env vars, or AWS config)
# ---------------------------------------------------------
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')

s3_client = boto3.client('s3', region_name=AWS_REGION)

# Upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file size

def get_db_connection():
    """Establishes and returns a connection to the MySQL database."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

# Success response template
SUCCESS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Successful</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <main class="page-container">
        <section class="registration-card" aria-labelledby="confirmation-title">
            <header class="card-header">
                <div class="badge" style="background-color: #ecfdf5; color: #059669;">Saved to S3 &amp; MySQL</div>
                <h1 id="confirmation-title">Registration Successful</h1>
                <p class="description">
                    Student registration record has been successfully persisted with photo stored in Amazon S3.
                </p>
            </header>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: 0.85rem;">
                <div>
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Student ID</span>
                    <p style="font-size: 1rem; font-weight: 600; color: #0f172a; margin-top: 0.2rem;">#{{ student_id }}</p>
                </div>
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
                    <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">S3 Photo Location</span>
                    <p style="font-size: 0.875rem; font-weight: 500; color: #0f172a; margin-top: 0.2rem; word-break: break-all;">{{ photo_url }}</p>
                </div>
            </div>

            <div style="padding: 0.85rem 1rem; background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px; margin-bottom: 1.5rem; font-size: 0.875rem; color: #1e40af; line-height: 1.4;">
                <strong>Integration Status:</strong> Photo uploaded to Amazon S3 (<code>{{ bucket_name }}</code>) and record saved to MySQL (<code>{{ db_name }}.students</code>).
            </div>

            <a href="/" class="submit-btn" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                Register Another Student
            </a>
        </section>
    </main>
</body>
</html>
"""

# Error response template for invalid form submission, S3 failures, or database errors
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
                <div class="badge" style="background-color: #fef2f2; color: #dc2626;">Error</div>
                <h1 id="error-title">Submission Failed</h1>
                <p class="description">
                    The registration request could not be processed:
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
    Receives and validates the submitted student registration form,
    uploads the photo to Amazon S3 using boto3, and inserts the record
    into MySQL studentdb.students.
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

    # 7. Upload photo to Amazon S3
    if not S3_BUCKET_NAME:
        app.logger.error("S3 upload failed: S3_BUCKET_NAME environment variable is not configured.")
        return render_template_string(
            ERROR_TEMPLATE,
            errors=["Storage service is not configured. Please configure S3_BUCKET_NAME."]
        ), 500

    safe_filename = secure_filename(photo.filename)
    unique_key = f"uploads/{uuid.uuid4().hex}_{safe_filename}"

    try:
        photo.seek(0)
        extra_args = {}
        if photo.content_type:
            extra_args['ContentType'] = photo.content_type

        s3_client.upload_fileobj(
            photo,
            S3_BUCKET_NAME,
            unique_key,
            ExtraArgs=extra_args if extra_args else None
        )

        # Build S3 reference URL
        if AWS_REGION:
            photo_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_key}"
        else:
            photo_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{unique_key}"

    except Exception as e:
        # Handle S3 errors safely without exposing AWS credentials or internal details
        app.logger.error("S3 upload failed: %s", type(e).__name__)
        return render_template_string(
            ERROR_TEMPLATE,
            errors=["A storage error occurred while uploading the photo. Please try again later."]
        ), 500

    # 8. Insert record into MySQL (only after successful S3 upload)
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            insert_sql = """
            INSERT INTO students (name, email, course, photo_url)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (name.strip(), email.strip(), course.strip(), photo_url))
            student_id = cursor.lastrowid
        connection.close()
    except Exception as e:
        # Handle database errors safely without exposing passwords or credentials
        app.logger.error("Database insertion failed: %s", type(e).__name__)
        return render_template_string(
            ERROR_TEMPLATE,
            errors=["A database error occurred while saving your registration. Please try again later."]
        ), 500

    # Render confirmation page with inserted record details
    return render_template_string(
        SUCCESS_TEMPLATE,
        student_id=student_id,
        name=name.strip(),
        email=email.strip(),
        course=course.strip(),
        photo_url=photo_url,
        bucket_name=S3_BUCKET_NAME,
        db_name=DB_NAME
    ), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
