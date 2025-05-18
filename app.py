from flask import Flask, render_template, request, redirect, session, url_for, send_file
from werkzeug.utils import secure_filename
import psycopg2, io, os
from waitress import serve
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", 5432)  # Default PostgreSQL port is 5432
)
#conn = psycopg2.connect(
 #   dbname="flaskapp",
  #  user="haron",
   # password="92949698",
    #host="localhost"
#)
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'client'
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    price DECIMAL(10, 2),
    image BYTEA
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS cart (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id)
);
""")
conn.commit()
 
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    cursor.execute("SELECT id, name, price, description FROM products")
    products = cursor.fetchall()
    return render_template('dashboard.html', products=products)

@app.route('/image/<int:product_id>')
def image(product_id):
    cursor.execute("SELECT image FROM products WHERE id = %s", (product_id,))
    result = cursor.fetchone()
    if result:
        return send_file(io.BytesIO(result[0]), mimetype='image/jpeg')
    return "Image not found", 404

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cursor.execute("SELECT id, name, description, price FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
    cursor.execute("INSERT INTO cart (user_id, product_id) VALUES (%s, %s)", (session['user_id'], product_id))
    conn.commit()
    return redirect(url_for('cart'))
    
   

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    cursor.execute("""
        SELECT products.name, products.price FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session['user_id'],))
    items = cursor.fetchall()
    return render_template('.html', items=items)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    # Manually set the role to 'admin' for testing (remove later for production)
    session['role'] = 'admin'  # For testing purposes, make sure to delete this after testing

    if session.get('role') != 'admin':
        return "Access denied"

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        image = request.files['image']

        if image:
            image_data = image.read()

            cursor.execute(
                "INSERT INTO products (name, price, description, image) VALUES (%s, %s, %s, %s)",
                (name, price, description, image_data)
            )
            conn.commit()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("admin.html", products=products)


@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('home'))
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    return redirect(url_for('admin'))
    
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute("SELECT id, password, role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['role'] = user[2]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except psycopg2.Error:
            return render_template('register.html', error="Username already taken")
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
