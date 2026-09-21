import io
import os
import re
import pymysql
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import app as flask_app
from app import app, get_db_connection

def run_tests():
    print("=== STARTING S3 + FLASK + MYSQL INTEGRATION TESTS ===")
    client = app.test_client()

    # 1. Test GET /
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200 for GET /, got {res.status_code}"
    assert b"Student Registration" in res.data, "Registration form missing in GET /"
    print("PASS: [1/9] GET / returns 200 OK and registration form")

    # 2. Test Missing Name
    res = client.post('/register', data={
        'name': '',
        'email': 'student@example.com',
        'course': 'Cloud Architecture',
        'photo': (io.BytesIO(b"fake image"), 'profile.png')
    }, content_type='multipart/form-data')
    assert res.status_code == 400, f"Expected 400 for missing name, got {res.status_code}"
    assert b"Student Name is required" in res.data
    print("PASS: [2/9] Missing Student Name rejected with 400 Bad Request")

    # 3. Test Invalid Email
    res = client.post('/register', data={
        'name': 'Test Student',
        'email': 'not-an-email',
        'course': 'Cloud Architecture',
        'photo': (io.BytesIO(b"fake image"), 'profile.png')
    }, content_type='multipart/form-data')
    assert res.status_code == 400, f"Expected 400 for invalid email, got {res.status_code}"
    assert b"A valid email address is required" in res.data
    print("PASS: [3/9] Invalid Email rejected with 400 Bad Request")

    # 4. Test Missing Course
    res = client.post('/register', data={
        'name': 'Test Student',
        'email': 'student@example.com',
        'course': '',
        'photo': (io.BytesIO(b"fake image"), 'profile.png')
    }, content_type='multipart/form-data')
    assert res.status_code == 400, f"Expected 400 for missing course, got {res.status_code}"
    assert b"Course selection is required" in res.data
    print("PASS: [4/9] Missing Course rejected with 400 Bad Request")

    # 5. Test Invalid Photo File Extension
    res = client.post('/register', data={
        'name': 'Test Student',
        'email': 'student@example.com',
        'course': 'Cloud Architecture',
        'photo': (io.BytesIO(b"binary"), 'malicious.exe')
    }, content_type='multipart/form-data')
    assert res.status_code == 400, f"Expected 400 for invalid extension, got {res.status_code}"
    assert b"Photo must be a valid image file" in res.data
    print("PASS: [5/9] Invalid Photo extension rejected with 400 Bad Request")

    # 6. Test Unconfigured S3_BUCKET_NAME
    with patch.object(flask_app, 'S3_BUCKET_NAME', None):
        res = client.post('/register', data={
            'name': 'Bucket Test',
            'email': 'nobucket@example.com',
            'course': 'Cloud Architecture',
            'photo': (io.BytesIO(b"image bytes"), 'test.jpg')
        }, content_type='multipart/form-data')
        assert res.status_code == 500, f"Expected 500 for unconfigured bucket, got {res.status_code}"
        assert b"Storage service is not configured" in res.data
        print("PASS: [6/9] Unconfigured S3_BUCKET_NAME safely handled with 500 without crashing")

    # 7. Test S3 Upload Failure Handling (Ensures MySQL record is NOT inserted)
    with patch.object(flask_app, 'S3_BUCKET_NAME', 'test-capstone-bucket'):
        with patch.object(flask_app.s3_client, 'upload_fileobj', side_effect=Exception("S3 Connection Timeout")):
            res = client.post('/register', data={
                'name': 'S3 Fail Student',
                'email': 's3fail@example.com',
                'course': 'Cloud Architecture',
                'photo': (io.BytesIO(b"image bytes"), 's3fail.jpg')
            }, content_type='multipart/form-data')
            assert res.status_code == 500, f"Expected 500 on S3 failure, got {res.status_code}"
            assert b"A storage error occurred while uploading the photo" in res.data

            # Verify NO MySQL record was inserted for this student
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM students WHERE email = %s", ('s3fail@example.com',))
                row = cursor.fetchone()
                assert row is None, "Integrity failure: Student was inserted into MySQL despite S3 upload failure!"
            conn.close()
            print("PASS: [7/9] S3 upload failure handled safely (500) and aborted MySQL insert")

    # 8. Test Successful S3 Upload + Unique Key + MySQL Insertion
    test_student = {
        'name': 'Priya Patel',
        'email': 'priya.patel@example.com',
        'course': 'AWS Cloud Architecture',
        'filename': 'priya_avatar.png'
    }
    mock_upload = MagicMock()
    with patch.object(flask_app, 'S3_BUCKET_NAME', 'student-registration-photos'):
        with patch.object(flask_app.s3_client, 'upload_fileobj', mock_upload):
            res = client.post('/register', data={
                'name': test_student['name'],
                'email': test_student['email'],
                'course': test_student['course'],
                'photo': (io.BytesIO(b"valid image data"), test_student['filename'])
            }, content_type='multipart/form-data')

            assert res.status_code == 200, f"Expected 200 for valid S3 registration, got {res.status_code}"
            assert b"Saved to S3" in res.data
            assert test_student['name'].encode() in res.data

            # Check mock upload arguments: bucket name, unique key pattern
            assert mock_upload.called, "s3_client.upload_fileobj was not called!"
            args, kwargs = mock_upload.call_args
            called_bucket = args[1]
            called_key = args[2]
            assert called_bucket == 'student-registration-photos', f"Wrong bucket: {called_bucket}"
            assert re.match(r"^uploads/[a-f0-9]{32}_priya_avatar\.png$", called_key), f"Key does not match unique pattern: {called_key}"

            # Verify MySQL record persistence
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, email, course, photo_url FROM students WHERE email = %s", (test_student['email'],))
                row = cursor.fetchone()
                assert row is not None, "Record not found in MySQL!"
                assert row['name'] == test_student['name']
                assert row['email'] == test_student['email']
                assert row['course'] == test_student['course']
                assert called_key in row['photo_url'], f"S3 key {called_key} not in stored photo_url {row['photo_url']}"
                print(f"PASS: [8/9] S3 upload simulated successfully! Unique Key: '{called_key}', Stored URL: '{row['photo_url']}'")
            conn.close()

    # 9. Test Database Error Handling after S3 upload
    with patch.object(flask_app, 'S3_BUCKET_NAME', 'student-registration-photos'):
        with patch.object(flask_app.s3_client, 'upload_fileobj', MagicMock()):
            with patch('app.get_db_connection', side_effect=pymysql.OperationalError(2003, "Can't connect to MySQL")):
                res = client.post('/register', data={
                    'name': 'DB Error Student',
                    'email': 'dberror@example.com',
                    'course': 'AWS Solutions',
                    'photo': (io.BytesIO(b"image data"), 'db_err.png')
                }, content_type='multipart/form-data')
                assert res.status_code == 500, f"Expected 500 on DB error, got {res.status_code}"
                assert b"A database error occurred while saving your registration" in res.data
                print("PASS: [9/9] Database error handled cleanly (500) without exposing credentials")

    print("\n=== ALL 9 S3 + FLASK + MYSQL INTEGRATION TESTS PASSED ===")

if __name__ == '__main__':
    run_tests()
