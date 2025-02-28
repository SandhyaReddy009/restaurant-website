from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory
from flask_pymongo import PyMongo
from datetime import datetime
import os
import logging
from bson import ObjectId

app = Flask(__name__)

# Session Configuration
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/sandhya_internship"
mongo = PyMongo(app)

# Models equivalent to MongoDB collections
registrations = mongo.db.registrations
table_bookings = mongo.db.tableBookings
carts = mongo.db.carts
orders = mongo.db.orders

# Setting up logging
logging.basicConfig(level=logging.DEBUG)

# Helper function to check if a user is logged in
def is_logged_in():
    if 'userId' not in session:
        return False
    return True

# Serve static files from the 'public' folder
@app.route('/<path:filename>')
def serve_html(filename):
    return send_from_directory(os.path.join(app.root_path, 'public'), filename)

# Routes
@app.route('/register.html')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    
    if password != confirm_password:
        return render_template('register.html', error="Passwords do not match")
    
    try:
        registrations.insert_one({'name': name, 'email': email, 'password': password})
        return redirect('/login.html')
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return render_template('register.html', error="An error occurred during registration")

@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/cart.html')
def cart():
    if not is_logged_in():
        return redirect('/login.html')

    userId = session['userId']
    cart_items = carts.find({'userId': userId})
    
    return render_template('cart.html', cart_items=cart_items)

@app.route('/login.html')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']
    
    if username == 'admin' and password == 'admin':
        return redirect('/admin.html')
    
    user = registrations.find_one({'name': username, 'password': password})
    
    if user:
        session['userId'] = str(user['_id'])
        session['username'] = username
        session['email'] = user['email']
        return redirect('/index.html')
    else:
        return render_template('login.html', error="Invalid username or password")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')

@app.route('/Biriyani.html')
def biriyani():
    return render_template('Biriyani.html')

@app.route('/Burgers.html')
def burgers():
    return render_template('Burgers.html')

@app.route('/Roti.html')
def roti():
    return render_template('Roti.html')

@app.route('/Salads.html')
def salads():
    return render_template('Salads.html')

@app.route('/Tandoori.html')
def tandoori():
    return render_template('Tandoori.html')

@app.route('/table_bookings.html')
def table_bookings_view():
    return render_template('table_bookings.html')

@app.route('/user_orders.html')
def user_orders():
    return render_template('user_orders.html')

# Add item to cart
@app.route('/cart', methods=['POST'])
def add_to_cart():
    if not is_logged_in():
        return redirect('/login.html')

    data = request.get_json()
    userId = session['userId']
    productId = data['productId']
    itemName = data['itemName']
    quantity = int(data['quantity'])
    price = float(data['price'])

    existing_item = carts.find_one({'userId': userId, 'productId': productId})
    
    if existing_item:
        carts.update_one({'_id': existing_item['_id']}, {'$inc': {'quantity': quantity}})
    else:
        carts.insert_one({'userId': userId, 'productId': productId, 'itemName': itemName, 'quantity': quantity, 'price': price})
    
    return jsonify({'message': 'Item added to cart'})

# Get cart items
@app.route('/cart', methods=['GET'])
def get_cart():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized'}), 401

    userId = session['userId']
    cart_items = carts.find({'userId': userId})
    return jsonify([{
        'productId': item['productId'],
        'itemName': item['itemName'],
        'quantity': item['quantity'],
        'price': item['price']
    } for item in cart_items])

from flask import request, jsonify
from bson import ObjectId

@app.route('/cart/<product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized'}), 401

    try:
        # Ensure product_id is treated as a string (if it's not ObjectId, no need to convert)
        print(f"Received product_id for deletion: {product_id}")
        
        # Remove the item from the cart using the product_id (it can be a string or an ObjectId depending on your schema)
        result = carts.delete_one({"productId": product_id})
        
        if result.deleted_count == 1:
            return jsonify({"message": "Item removed successfully"}), 200
        else:
            return jsonify({"message": "Item not found"}), 404
    except Exception as e:
        print(f"Error: {e}")  # Log the error for debugging
        return jsonify({"error": str(e)}), 400



@app.route('/place-order', methods=['POST'])
def place_order():
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    if not data or 'paymentMethod' not in data or 'shippingAddress' not in data:
        return jsonify({'error': 'Payment method and shipping address are required'}), 400

    paymentMethod = data['paymentMethod']
    shippingAddress = data['shippingAddress']
    userId = session['userId']

    cart_items = list(carts.find({'userId': userId}))
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

    totalAmount = sum(item['price'] * item['quantity'] for item in cart_items)
    order_data = {
        'userId': userId,
        'items': cart_items,
        'totalAmount': totalAmount,
        'paymentMethod': paymentMethod,
        'shippingAddress': shippingAddress,
        'orderDate': datetime.now()
    }

    orders.insert_one(order_data)
    carts.delete_many({'userId': userId})

    return jsonify({'message': 'Order placed successfully', 'redirect': '/orders.html'}), 200

@app.route('/orders.html')
def orders_page():
    if not is_logged_in():
        return redirect('/login.html')
    
    userId = session['userId']
    user_orders = orders.find({'userId': userId})
    
    return render_template('orders.html', orders=user_orders)

@app.route('/api/userSession', methods=['GET'])
def user_session():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized'}), 401
    user = mongo.db.registrations.find_one({'_id': ObjectId(session['userId'])})
    if user:
        return jsonify({'username': user['name'], 'email': user['email']})
    return jsonify({'message': 'User not found'}), 404



@app.route('/api/orders', methods=['GET'])
def get_orders():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized'}), 401

    orders = mongo.db.orders.find({'userId': session['userId']})
    orders_data = [{
        'orderId': str(order['_id']),
        'date': order['orderDate'],
        'totalAmount': order['totalAmount'],
        'shippingAddress': order['shippingAddress']
    } for order in orders]

    return jsonify(orders_data)

@app.route('/admin.html')
def admin():
    return render_template('admin.html')

from bson import ObjectId
from flask import jsonify

# Helper function to convert ObjectId to string
def objectid_to_str(obj):
    if isinstance(obj, ObjectId):  # If it's an ObjectId, convert it to string
        return str(obj)
    elif isinstance(obj, dict):  # If it's a dictionary, apply recursively
        return {key: objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):  # If it's a list, apply recursively
        return [objectid_to_str(item) for item in obj]
    else:
        return obj 


@app.route('/api/admin/orders', methods=['GET'])
def admin_orders():
    admin_orders = mongo.db.orders.find()  # Fetch orders from the database
    orders_list = []

    for order in admin_orders:
        order = objectid_to_str(order)  # Ensure all ObjectIds are converted to strings
        orders_list.append(order)

    return jsonify(orders_list)




@app.route('/bookTable', methods=['POST'])
def book_table():
    if not is_logged_in():
        return redirect('/login.html')

    username = session['username']
    email = session['email']
    date = request.form['date']
    time = request.form['time']
    people = int(request.form['people'])
    phone = request.form['phone']

    formatted_date = datetime.strptime(date, '%d-%m-%Y')
    table_bookings.insert_one({
        'username': username,
        'email': email,
        'date': formatted_date,
        'time': time,
        'people': people,
        'phone': phone
    })
    return redirect('/index.html')

@app.route('/bookings.html')
def bookings():
    if not is_logged_in():
        return redirect('/login.html')
    
    return render_template('bookings.html')



from bson import ObjectId
from flask import jsonify, session

# Helper function to convert ObjectId to string
def objectid_to_str(obj):
    if isinstance(obj, ObjectId):  # If it's an ObjectId, convert it to string
        return str(obj)
    elif isinstance(obj, dict):  # If it's a dictionary, apply recursively
        return {key: objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):  # If it's a list, apply recursively
        return [objectid_to_str(item) for item in obj]
    else:
        return obj  # If it's neither, return the object as is

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized'}), 401
    
    # Fetch all the bookings from the collection (not filtered by userId)
    table_bookings = mongo.db.tableBookings.find()  # Remove the filter by 'userId'
    
    # Iterate over the cursor and create the booking data list
    bookings_data = [{
        'username': booking['username'],
        'email': booking['email'],
        'date': booking['date'],
        'time': booking['time'],
        'people': booking['people'],
        'phone': booking['phone']
    } for booking in table_bookings]

    return jsonify(bookings_data)








@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    users = registrations.find({}, {'name': 1, 'email': 1})
    return jsonify([{
        'name': user['name'],
        'email': user['email']
    } for user in users])

if __name__ == '__main__':
    app.run(debug=True, port=3000)
