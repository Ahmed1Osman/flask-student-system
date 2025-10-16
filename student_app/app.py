from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import get_connection, init_db
from werkzeug.utils import secure_filename
from functools import wraps
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'ahmed'  # Required for sessions
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}})

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API Authentication decorator
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        # Simple API key check (in production, store this securely)
        if api_key != 'your-secret-api-key-123':
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/template')
def test_template():
    return render_template('test.html')

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize database
print("Initializing database...")
init_db()
print("Database initialization complete!")

# -------------------- User Class --------------------
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['password'])
    return None

# -------------------- Auth Routes --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        conn = get_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except:
            flash("Username already exists.", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template('login.html')
            
        conn = get_connection()
        try:
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            
            if user:
                if bcrypt.check_password_hash(user['password'], password):
                    user_obj = User(user['id'], user['username'], user['password'])
                    login_user(user_obj)
                    next_page = request.args.get('next')
                    flash("Login successful!", "success")
                    return redirect(next_page or url_for('index'))
                else:
                    flash("Invalid username or password.", "danger")
            else:
                flash("User not found.", "danger")
                
        except Exception as e:
            print(f"Login error: {e}")
            flash("An error occurred during login. Please try again.", "danger")
        finally:
            conn.close()
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# -------------------- Student Routes --------------------
@app.route('/')
@login_required
def index():
    conn = get_connection()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template('index.html', students=students, user=current_user.username)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        city = request.form['city']
        
        # Handle file upload
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Create unique filename
                import time
                unique_filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                image_filename = unique_filename
        
        conn = get_connection()
        conn.execute("INSERT INTO students (name, age, city, image) VALUES (?, ?, ?, ?)", 
                     (name, age, city, image_filename))
        conn.commit()
        conn.close()
        flash("Student added successfully!", "success")
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    conn = get_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        city = request.form['city']
        
        # Get current student data
        student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
        current_image = student['image'] if student else None
        
        # Handle file upload
        image_filename = current_image
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Delete old image if exists
                if current_image:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], current_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(file.filename)
                import time
                unique_filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                image_filename = unique_filename
        
        conn.execute("UPDATE students SET name=?, age=?, city=?, image=? WHERE id=?", 
                     (name, age, city, image_filename, id))
        conn.commit()
        conn.close()
        flash("Student updated successfully!", "success")
        return redirect(url_for('index'))
    
    # GET request - fetch student data
    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    conn.close()
    
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for('index'))
    
    return render_template('edit.html', student=student)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    conn = get_connection()
    try:
        student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
        
        if student is None:
            flash("Student not found.", "danger")
        else:
            # Delete image file if exists
            if student['image']:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], student['image'])
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            conn.execute("DELETE FROM students WHERE id=?", (id,))
            conn.commit()
            flash("Student deleted successfully!", "success")
    except Exception as e:
        print(f"Delete error: {e}")
        flash("An error occurred while deleting the student.", "danger")
    finally:
        conn.close()
    
    return redirect(url_for('index'))

# -------------------- API Routes --------------------
@app.route('/api/students', methods=['GET'])
@api_key_required
def api_get_students():
    """Get all students"""
    try:
        conn = get_connection()
        students = conn.execute("SELECT * FROM students").fetchall()
        conn.close()
        
        students_list = []
        for student in students:
            students_list.append({
                'id': student['id'],
                'name': student['name'],
                'age': student['age'],
                'city': student['city'],
                'image': student['image'],
                'image_url': url_for('static', filename=f"uploads/{student['image']}", _external=True) if student['image'] else None,
                'created_at': student['created_at']
            })
        
        return jsonify({
            'success': True,
            'count': len(students_list),
            'data': students_list
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students/<int:id>', methods=['GET'])
@api_key_required
def api_get_student(id):
    """Get a single student by ID"""
    try:
        conn = get_connection()
        student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
        conn.close()
        
        if student is None:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        student_data = {
            'id': student['id'],
            'name': student['name'],
            'age': student['age'],
            'city': student['city'],
            'image': student['image'],
            'image_url': url_for('static', filename=f"uploads/{student['image']}", _external=True) if student['image'] else None,
            'created_at': student['created_at']
        }
        
        return jsonify({
            'success': True,
            'data': student_data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students', methods=['POST'])
@api_key_required
def api_create_student():
    """Create a new student"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        name = data.get('name')
        age = data.get('age')
        city = data.get('city')
        
        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO students (name, age, city) VALUES (?, ?, ?)",
            (name, age, city)
        )
        student_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'data': {
                'id': student_id,
                'name': name,
                'age': age,
                'city': city
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students/<int:id>', methods=['PUT'])
@api_key_required
def api_update_student(id):
    """Update a student"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        conn = get_connection()
        student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
        
        if student is None:
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        name = data.get('name', student['name'])
        age = data.get('age', student['age'])
        city = data.get('city', student['city'])
        
        conn.execute(
            "UPDATE students SET name=?, age=?, city=? WHERE id=?",
            (name, age, city, id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Student updated successfully',
            'data': {
                'id': id,
                'name': name,
                'age': age,
                'city': city
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students/<int:id>', methods=['DELETE'])
@api_key_required
def api_delete_student(id):
    """Delete a student"""
    try:
        conn = get_connection()
        student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
        
        if student is None:
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Delete image file if exists
        if student['image']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], student['image'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        conn.execute("DELETE FROM students WHERE id=?", (id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Student deleted successfully'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@api_key_required
def api_get_stats():
    """Get statistics about students"""
    try:
        conn = get_connection()
        
        # Total students
        total = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()['count']
        
        # Average age
        avg_age = conn.execute("SELECT AVG(age) as avg_age FROM students").fetchone()['avg_age']
        
        # Students by city
        cities = conn.execute("""
            SELECT city, COUNT(*) as count 
            FROM students 
            WHERE city IS NOT NULL 
            GROUP BY city 
            ORDER BY count DESC
        """).fetchall()
        
        conn.close()
        
        cities_data = [{'city': c['city'], 'count': c['count']} for c in cities]
        
        return jsonify({
            'success': True,
            'data': {
                'total_students': total,
                'average_age': round(avg_age, 2) if avg_age else 0,
                'students_by_city': cities_data
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """API Documentation"""
    docs = {
        'api_version': '1.0',
        'base_url': request.url_root + 'api',
        'authentication': {
            'type': 'API Key',
            'header': 'X-API-Key',
            'example': 'X-API-Key: your-secret-api-key-123'
        },
        'endpoints': [
            {
                'method': 'GET',
                'path': '/api/students',
                'description': 'Get all students',
                'auth_required': True
            },
            {
                'method': 'GET',
                'path': '/api/students/<id>',
                'description': 'Get a single student by ID',
                'auth_required': True
            },
            {
                'method': 'POST',
                'path': '/api/students',
                'description': 'Create a new student',
                'auth_required': True,
                'body': {
                    'name': 'string (required)',
                    'age': 'integer (optional)',
                    'city': 'string (optional)'
                }
            },
            {
                'method': 'PUT',
                'path': '/api/students/<id>',
                'description': 'Update a student',
                'auth_required': True,
                'body': {
                    'name': 'string (optional)',
                    'age': 'integer (optional)',
                    'city': 'string (optional)'
                }
            },
            {
                'method': 'DELETE',
                'path': '/api/students/<id>',
                'description': 'Delete a student',
                'auth_required': True
            },
            {
                'method': 'GET',
                'path': '/api/stats',
                'description': 'Get statistics about students',
                'auth_required': True
            }
        ]
    }
    return jsonify(docs), 200

@app.route('/api-test')
def api_test_page():
    """Serve the API testing page"""
    return render_template('api_test.html')

# Test route to check if templates are working
@app.route('/test')
def test():
    return "<h1>Test Route Works!</h1><p>If you can see this, Flask is working!</p>"

if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"Debug mode: {app.debug}")
    print(f"Templates directory: {app.template_folder}")
    app.run(debug=True, port=5001)  # Changed port to 5001 to avoid conflicts