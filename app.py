from flask import Flask, request, render_template, redirect, url_for, flash, session ,send_file, jsonify
from functools import wraps
import bcrypt
import pytz
from datetime import datetime, timezone, timedelta
import csv
import json
import os
import uuid
import io
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

now = datetime.now()  # Works fine after the correct import
print(now)

app = Flask(__name__)

app.secret_key = os.urandom(24)

# 读取产品数据
def load_data_from_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

# 保存数据到 JSON 文件
def save_data_to_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")


# 首页
@app.route('/')
def index():
    user_count = len(load_data_from_json('users.json'))
    order_count = len(load_data_from_json('orders.json'))
    product_count = len(load_data_from_json('products.json'))

    # 检查用户是否登录
    is_logged_in = 'email' in session

    return render_template('index.html', user_count=user_count, order_count=order_count, product_count=product_count, is_logged_in=is_logged_in)

    # app.py
@app.route('/products_custom', methods=['GET'])
def products_custom():
        page = request.args.get('page', 1, type=int)
        per_page = 30
        search_query = request.args.get('search', '').lower()

        try:
            products = load_data_from_json('products.json')
        except Exception as e:
            return f"Error loading products: {e}", 500

        # 篩選產品（根據搜尋字串）
        if search_query:
            products = [
                product for product in products
                if ('name' in product and search_query in product['name'].lower()) or
                   ('description' in product and search_query in product['description'].lower())
            ]

        # 計算總頁數並分頁顯示
        total_pages = (len(products) + per_page - 1) // per_page
        paginated_products = products[(page - 1) * per_page: page * per_page]

        return render_template(
            'products_custom.html',
            products=paginated_products,
            page=page,
            total_pages=total_pages,
            search_query=search_query
        )



# 购物车功能
@app.route('/cart')
def cart():
        cart = session.get('cart', [])
        total_price = 0

        # 計算總價格
        for item in cart:
            item_price = item['salePrice'] if item['salePrice'] > 0 else item['price']
            total_price += item['quantity'] * item_price

        return render_template('cart.html', cart_products=cart, total_price=total_price)

@app.route('/add_to_cart/<string:product_uid>', methods=['POST'])
def add_to_cart(product_uid):
                # 加載產品資料
                products = load_data_from_json('products.json')

                # 查找產品，並確保產品資料中包含 'uid' 鍵
                product = next((p for p in products if p.get('uid') == product_uid), None)

                if product is None:
                    return jsonify({'success': False, 'message': 'Product not found!'}), 404

                # 確認產品包含必要的鍵，並防止 KeyError
                name = product.get('name', 'Unnamed Product')
                price = product.get('price', 0)
                salePrice = product.get('salePrice', price)  # 如果 salePrice 不存在則預設為 price

                # 從 session 中獲取或初始化購物車
                cart = session.get('cart', [])

                # 檢查產品是否已在購物車中
                for item in cart:
                    if item.get('uid') == product_uid:
                        item['quantity'] += 1
                        break
                else:
                    # 如果產品不在購物車中，則添加新項目
                    cart.append({
                        'uid': product_uid,
                        'name': name,
                        'salePrice': salePrice,
                        'price': price,
                        'quantity': 1,
                    })

                # 更新 session 中的購物車
                session['cart'] = cart

                # 跳轉到購物車頁面
                return redirect(url_for('cart'))



@app.route('/remove_from_cart/<string:product_uid>', methods=['POST'])
def remove_from_cart(product_uid):
    # Get the cart from the session
    cart = session.get('cart', [])
    # Filter out the product to remove it
    cart = [item for item in cart if item['uid'] != product_uid]
    # Save the updated cart back to session
    session['cart'] = cart
    flash('Product removed from cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_email = session.get('email')  # Fetch user email from session

    if request.method == 'POST':
        # Get shipping information from form
        shipping_info = {field: request.form.get(field) for field in ['fullName', 'email', 'address', 'city', 'zipcode', 'country']}

        # Ensure all fields are filled
        if not all(shipping_info.values()):
            flash('Please fill in all required shipping fields.', 'danger')
            return render_template('checkout.html', cart_products=session.get('cart', []), total_price=0, user_email=user_email)

        # Calculate total price
        cart_items = session.get('cart', [])
        total_price = sum(item.get('salePrice', item['price']) * item['quantity'] for item in cart_items)

        # Create and save the order
        order_data = {
            'orderNumber': str(uuid.uuid4()),
            'products': cart_items,
            'totalPrice': total_price,
            'status': 'Pending',
            'owner': shipping_info['fullName'],
            'timeCreated': datetime.now().isoformat(),
            'shipping': shipping_info
        }

        orders = load_data_from_json('orders.json')
        orders.append(order_data)
        save_data_to_json('orders.json', orders)

        session.pop('cart', None)  # Clear the cart after checkout
        flash('Checkout successful! Your order has been placed.', 'success')
        return redirect(url_for('products_custom'))

    # GET request: Render checkout page with cart and total price
    cart_items = session.get('cart', [])
    total_price = sum(item.get('salePrice', item['price']) * item['quantity'] for item in cart_items)
    return render_template('checkout.html', cart_products=cart_items, total_price=total_price, user_email=user_email)


@app.route('/orders_history')
def orders_history():
        email = session.get('email')  # Get the logged-in user's email from session
        if not email:
            flash('Please log in to view your orders.', 'danger')
            return redirect(url_for('login'))

        orders = load_data_from_json('orders.json')

        # Get China Standard Time (GMT+8)
        tz = pytz.timezone('Asia/Shanghai')

        # Filter orders by shipping email
        user_orders = []
        for order in orders:
            if 'shipping' in order and order['shipping'].get('email') == email:
                # Convert the order datetime to GMT+8
                if 'timeCreated' in order:
                    try:
                        # Assuming 'timeCreated' is in ISO 8601 format
                        order_time = datetime.fromisoformat(order['timeCreated'])
                        order_time = pytz.utc.localize(order_time)  # Localize the time to UTC first
                        order_time = order_time.astimezone(tz)  # Convert to CST (GMT+8)

                        # Format datetime as "YYYY-MM-DD HH:MM:SS"
                        order['formatted_time'] = order_time.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        print(f"Error in time conversion: {e}")
                        order['formatted_time'] = "時間格式錯誤"

                user_orders.append(order)

        # Check if the user has no orders
        if not user_orders:
            flash('You have no orders to display.', 'info')

        return render_template('orders_history.html', orders=user_orders)


@app.route('/register', methods=['GET', 'POST'])
def register():
            if request.method == 'POST':
                email = request.form.get('email')
                password = request.form.get('password')
                display_name = request.form.get('display_name')

                # 加载现有用户数据
                users = load_data_from_json('users.json')

                # 检查用户是否已存在
                if any(user['email'] == email for user in users):
                    flash('User already exists!', 'danger')
                    return redirect(url_for('register'))

                # 对密码进行哈希处理
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # 获取当前时间（台北时区）
                tz = pytz.timezone('Asia/Taipei')
                current_time = datetime.now(tz).isoformat()

                # 创建新用户数据
                user_data = {
                    'uid': str(uuid.uuid4()),
                    'email': email,
                    'password': hashed_password,
                    'display_name': display_name,
                    'created_time': current_time,
                }

                # 添加新用户数据并保存
                users.append(user_data)
                save_data_to_json('users.json', users)

                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))

            # 请求为 GET 时，返回注册页面
            return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            # 加载用户数据
            users = load_data_from_json('users.json')
            print(users)  # 打印用户数据，确保加载正确

            # 查找用户
            user = next((user for user in users if user['email'] == email), None)

            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['email'] = email
                flash('Login successful!', 'success')
                return redirect(url_for('products_custom'))
            else:
                flash('Invalid credentials. Please try again.', 'danger')

        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)  # Remove the email from the session to log out
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# 产品管理路由
@app.route('/products', methods=['GET', 'POST'])
def manage_products():
    if request.method == 'POST':
        product_data = {
            'uid': str(uuid.uuid4()),
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'salePrice': float(request.form['salePrice']),
            'category': request.form['category'],
            'createdTime': datetime.datetime.now().isoformat(),
            'owner': request.form['owner'],
            'tags': request.form.getlist('tags')
        }

        products = load_data_from_json('products.json')
        products.append(product_data)
        save_data_to_json('products.json', products)

        return redirect(url_for('manage_products'))

    products = load_data_from_json('products.json')
    return render_template('products.html', products=products)

# 编辑和删除产品功能
@app.route('/products/edit/<string:uid>', methods=['GET', 'POST'])
def edit_product(uid):
    products = load_data_from_json('products.json')

    product = next((p for p in products if p['uid'] == uid), None)
    if product is None:
        return "Product not found", 404

    if request.method == 'POST':
        product['name'] = request.form['name']
        product['description'] = request.form['description']
        product['price'] = float(request.form['price'])
        product['salePrice'] = float(request.form.get('salePrice', 0))
        product['category'] = request.form['category']
        product['owner'] = request.form['owner']

        tags_input = request.form.get('tags', '')
        product['tags'] = [tag.strip() for tag in tags_input.split(',') if tag.strip()]

        save_data_to_json('products.json', products)

        return redirect(url_for('manage_products'))

    return render_template('product_edit.html', product=product)

@app.route('/products/delete/<string:uid>', methods=['GET', 'POST'])
def delete_product(uid):
    products = load_data_from_json('products.json')

    product = next((p for p in products if p.get('uid') == uid), None)

    if product is None:
        flash('Product not found!', 'danger')
        return redirect(url_for('manage_products'))

    if request.method == 'POST':
        products = [p for p in products if p.get('uid') != uid]
        save_data_to_json('products.json', products)

        flash('Product deleted successfully!', 'success')
        return redirect(url_for('manage_products'))

    return render_template('product_delete.html', product=product)


# 用户管理页面
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if request.method == 'POST':
        # 创建新用户
        user_data = {
            'email': request.form['email'],
            'display_name': request.form['display_name'],
            'photo_url': request.form['photo_url'],
            'phone_number': request.form['phone_number'],
            'student_id': request.form['student_id'],
            'ftt_auth': request.form['ftt_auth'],
            'group': request.form['group'],
            'title': request.form['title'],
            'created_time': datetime.datetime.now().isoformat(),
            'last_active_time': datetime.datetime.now().isoformat(),
            'blockedUsers': [],
            'addresses': []
        }

        # 保存新用户到本地 JSON 文件
        users = load_data_from_json('users.json')
        users.append(user_data)
        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)

        return redirect(url_for('manage_users'))

    users = load_data_from_json('users.json')
    return render_template('users.html', users=users)

@app.route('/orders', methods=['GET', 'POST'])
def manage_orders():
        if request.method == 'POST':
            # Create a new order
            order_data = {
                'orderNumber': str(uuid.uuid4()),  # Generate UUID for the order number
                'products': request.form.getlist('products'),  # Get product list from form
                'totalPrice': float(request.form['totalPrice']),
                'status': request.form['status'],
                'owner': request.form['owner'],
                'timeCreated': datetime.now().isoformat(),  # Store datetime as ISO string
                'shipping': {
                    'fullName': request.form['fullName'],
                    'email': request.form['email'],
                    'address': request.form['address'],
                    'city': request.form['city'],
                    'zipcode': request.form['zipcode'],
                    'country': request.form['country']
                }
            }

            # Save new order to JSON file
            orders = load_data_from_json('orders.json')
            orders.append(order_data)
            save_data_to_json('orders.json', orders)

            flash('Order created successfully!', 'success')
            return redirect(url_for('manage_orders'))

        # GET request, load existing orders and display
        orders = load_data_from_json('orders.json')

        # Define the GMT+8 timezone
        tz = pytz.timezone('Asia/Taipei')

        # Format the timeCreated field to 'YYYY-MM-DD HH:MM:SS' in GMT+8
        for order in orders:
            # Convert timeCreated from string to datetime object
            time_created = datetime.fromisoformat(order['timeCreated'])
            # Localize to GMT+8 timezone
            time_created = time_created.astimezone(tz)
            # Format the datetime object
            order['formattedTimeCreated'] = time_created.strftime('%Y-%m-%d %H:%M:%S')

        return render_template('orders.html', orders=orders)

@app.route('/download_orders_csv')
def download_orders_csv():
    # Load orders data
    orders = load_data_from_json('orders.json')

    # Create an in-memory buffer to store CSV data as bytes
    output = io.StringIO()  # Use StringIO for text data
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(['Order Number', 'Products', 'Total Price', 'Status', 'Owner', 'Created Time', 'Shipping Full Name', 'Shipping Email', 'Shipping Address', 'Shipping City', 'Shipping Zipcode', 'Shipping Country'])

    # Write each order data as a row in the CSV
    for order in orders:
        products = ', '.join([str(product) for product in order['products']])  # Join product names if there are multiple
        writer.writerow([
            order['orderNumber'],
            products,
            order['totalPrice'],
            order['status'],
            order['owner'],
            order['timeCreated'],
            order['shipping']['fullName'],
            order['shipping']['email'],
            order['shipping']['address'],
            order['shipping']['city'],
            order['shipping']['zipcode'],
            order['shipping']['country']
        ])

    # Move the buffer position to the beginning of the file
    output.seek(0)

    # Send the CSV as a downloadable file
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='orders.csv')

@app.route('/download_orders_xlsx')
def download_orders_xlsx():
    # Load orders data
    orders = load_data_from_json('orders.json')

    # Create an in-memory buffer to store Excel data
    output = io.BytesIO()

    # Create a workbook and an active worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"

    # Write the header row
    headers = ['Order Number', 'Products', 'Total Price', 'Status', 'Owner', 'Created Time', 
               'Shipping Full Name', 'Shipping Email', 'Shipping Address', 'Shipping City', 
               'Shipping Zipcode', 'Shipping Country']
    ws.append(headers)

    # Write each order data as a row in the Excel sheet
    for order in orders:
        products = ', '.join([str(product) for product in order['products']])  # Join product names if there are multiple
        ws.append([
            order['orderNumber'],
            products,
            order['totalPrice'],
            order['status'],
            order['owner'],
            order['timeCreated'],
            order['shipping']['fullName'],
            order['shipping']['email'],
            order['shipping']['address'],
            order['shipping']['city'],
            order['shipping']['zipcode'],
            order['shipping']['country']
        ])

    # Save the workbook to the in-memory buffer
    wb.save(output)

    # Move the buffer position to the beginning of the file
    output.seek(0)

    # Send the Excel file as a downloadable response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                     as_attachment=True, download_name='orders.xlsx')


@app.route('/orders/edit/<string:order_number>', methods=['GET', 'POST'])
def edit_order(order_number):
        # 从文件中加载订单数据
        orders = load_data_from_json('orders.json')

        # 查找订单
        order = next((order for order in orders if order['orderNumber'] == order_number), None)

        if not order:
            return "Order not found", 404

        if request.method == 'POST':
            # 编辑订单数据
            order['status'] = request.form['status']
            order['totalPrice'] = float(request.form['totalPrice'])
            order['owner'] = request.form['owner']

            # 更新地址
            order['shipping']['address'] = {
                'address': request.form['address'],
                'city': request.form['city'],
                'zipcode': request.form['zipcode'],
                'country': request.form['country']
            }

            # 将更新后的订单保存到文件
            save_data_to_json('orders.json', orders)

            return redirect(url_for('manage_orders'))  # 跳转到订单管理页面

        # 渲染编辑页面
        return render_template('orders_edit.html', order=order)

@app.route('/orders/delete/<string:order_number>', methods=['GET', 'POST'])
def delete_order(order_number):
    # Load the orders from the JSON file
    orders = load_data_from_json('orders.json')

    # Find the order to delete
    order_to_delete = next((order for order in orders if order['orderNumber'] == order_number), None)

    if order_to_delete:
        if request.method == 'POST':
            # Remove the order from the list
            orders = [order for order in orders if order['orderNumber'] != order_number]
            # Save the updated orders list back to the JSON file
            save_data_to_json('orders.json', orders)
            flash('Order deleted successfully!', 'success')
            return redirect(url_for('manage_orders'))  # Redirect to orders management page

        # Render the confirmation page if it's a GET request
        return render_template('orders_delete.html', order=order_to_delete)

    else:
        flash('Order not found!', 'danger')
        return redirect(url_for('manage_orders'))  # Redirect if order is not found


@app.route('/user_setting', methods=['GET', 'POST'])
def user_setting():
    users = load_data_from_json('users.json')

    if request.method == 'POST':
        # 获取要更新的用户
        email = request.form['email']
        new_role = request.form['role']

        # 查找用户并更新其角色
        for user in users:
            if user['email'] == email:
                user['role'] = new_role
                break

        # 保存更新后的用户数据
        save_data_to_json('users.json', users)
        flash(f"User {email}'s role has been updated to {new_role}.", 'success')

    return render_template('user_setting.html', users=users)



# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)