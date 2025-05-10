from flask import Flask, render_template, request, redirect, session, url_for, send_file
from werkzeug.utils import secure_filename
import psycopg2, io, os
from waitress import serve


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="flaskapp",
    user="haron",
    password="92949698",
    host="localhost"
)
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
    # Directly go to the dashboard, assuming user is logged in
    if 'user_id' not in session:
        session['user_id'] = 1  # Manually set a user_id (for testing purposes, change as needed)
        session['role'] = 'client'  # Assume a 'client' role for the user (you can adjust this logic)
    return redirect(url_for('dashboard'))

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
    return render_template('cart.html', items=items)

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    serve(app,host="0.0.0.0",port=8000)
