from flask import Flask, request, render_template, redirect, url_for
import datetime
import json
import os
import uuid
from models import Product, db  # Import the Product model from models.py


app = Flask(__name__)

# 读取 products.json 文件的函数
def load_products_from_json():
    try:
        with open('product.json', 'r', encoding='utf-8') as file:
            products = json.load(file)
        if isinstance(products, list):  # 确保是列表格式
            return products
        else:
            return []  # 如果不是列表，返回空列表
    except Exception as e:
        print(f"Error loading products: {e}")
        return []  # 返回空列表

# 模拟从本地 JSON 文件加载数据
def load_data_from_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

# 首页
@app.route('/')
def index():
    # 从本地 JSON 文件读取数据
    user_count = len(load_data_from_json('users.json'))
    order_count = len(load_data_from_json('orders.json'))
    product_count = len(load_data_from_json('products.json'))

    # 将这些统计数据传递到模板
    return render_template('index.html', user_count=user_count, order_count=order_count, product_count=product_count)

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

# 订单管理页面
@app.route('/orders', methods=['GET', 'POST'])
def manage_orders():
    if request.method == 'POST':
        # 创建新订单
        order_data = {
            'products': request.form.getlist('products'),
            'totalPrice': float(request.form['totalPrice']),
            'tax': float(request.form['tax']),
            'status': request.form['status'],
            'orderNumber': int(request.form['orderNumber']),
            'owner': request.form['owner'],
            'timeCreated': datetime.datetime.now().isoformat(),
            'address': {
                'latLong': {
                    'lat': float(request.form['lat']),
                    'lng': float(request.form['lng'])
                },
                'name': request.form['address_name'],
                'streetAddress': request.form['streetAddress'],
                'city': request.form['city'],
                'state': request.form['state'],
                'postalCode': request.form['postalCode']
            }
        }

        # 保存新订单到本地 JSON 文件
        orders = load_data_from_json('orders.json')
        orders.append(order_data)
        with open('orders.json', 'w', encoding='utf-8') as file:
            json.dump(orders, file, ensure_ascii=False, indent=4)

        return redirect(url_for('manage_orders'))

    orders = load_data_from_json('orders.json')
    return render_template('orders.html', orders=orders)


# 产品管理页面
@app.route('/products', methods=['GET', 'POST'])
def manage_products():
        if request.method == 'POST':
            # 创建新产品，添加唯一的 UID
            product_data = {
                'uid': str(uuid.uuid4()),  # 生成唯一的 UID
                'name': request.form['name'],
                'description': request.form['description'],
                'price': float(request.form['price']),
                'salePrice': float(request.form['salePrice']),
                'category': request.form['category'],
                'createdTime': datetime.datetime.now().isoformat(),
                'owner': request.form['owner'],
                'tags': request.form.getlist('tags')
            }

            # 保存新产品到本地 JSON 文件
            products = load_data_from_json('products.json')
            products.append(product_data)
            with open('products.json', 'w', encoding='utf-8') as file:
                json.dump(products, file, ensure_ascii=False, indent=4)

            return redirect(url_for('manage_products'))

        products = load_data_from_json('products.json')
        return render_template('products.html', products=products)
    
@app.route('/products/edit/<string:uid>', methods=['GET', 'POST'])
def edit_product(uid):
        # Load existing products data
        products = load_data_from_json('products.json')

        # Find the product by UID
        product = next((p for p in products if p['uid'] == uid), None)
        if product is None:
            return "Product not found", 404

        if request.method == 'POST':
            # Update product fields with form data
            product['name'] = request.form['name']
            product['description'] = request.form['description']
            product['price'] = float(request.form['price'])
            product['salePrice'] = float(request.form.get('salePrice', 0))
            product['category'] = request.form['category']
            product['owner'] = request.form['owner']

            # Split tags by commas and remove any extra whitespace
            tags_input = request.form.get('tags', '')
            product['tags'] = [tag.strip() for tag in tags_input.split(',') if tag.strip()]

            # Handle cover image and additional images (if provided)
            product['coverImage'] = request.form['cover_image']
            images_input = request.form.get('images', '')
            product['images'] = [img.strip() for img in images_input.split(',') if img.strip()]

            # Save the updated list to JSON
            with open('products.json', 'w', encoding='utf-8') as file:
                json.dump(products, file, ensure_ascii=False, indent=4)

            return redirect(url_for('manage_products'))

        return render_template('edit.html', product=product)


@app.route('/products/delete/<string:uid>', methods=['GET', 'POST'])
def delete_product(uid):
        try:
            # Load the existing products from the JSON file
            with open('products.json', 'r') as f:
                products = json.load(f)

            # Find the product by its UID, handle the case where the UID might not exist
            product = next((p for p in products if p.get('uid') == uid), None)

            if product is None:
                flash('Product not found!', 'danger')
                return redirect(url_for('manage_products'))  # Adjust the redirect as needed

            if request.method == 'POST':
                if request.form.get('_method') == 'DELETE':  # Simulating DELETE method
                    # Remove the product from the list
                    products = [p for p in products if p.get('uid') != uid]

                    # Save the updated list back to the JSON file
                    with open('products.json', 'w') as f:
                        json.dump(products, f, indent=4)

                    flash('Product deleted successfully!', 'success')
                    return redirect(url_for('manage_products'))  # Adjust the redirect as needed

            return render_template('delete.html', product=product)

        except json.JSONDecodeError:
            flash('Error reading the products file!', 'danger')
            return redirect(url_for('manage_products'))

    
# 地址管理页面
@app.route('/addresses', methods=['GET', 'POST'])
def manage_addresses():
    if request.method == 'POST':
        # 创建新地址
        address_data = {
            'latLong': {
                'lat': float(request.form['lat']),
                'lng': float(request.form['lng'])
            },
            'name': request.form['name'],
            'streetAddress': request.form['streetAddress'],
            'streetAddress2': request.form['streetAddress2'],
            'city': request.form['city'],
            'state': request.form['state'],
            'postalCode': request.form['postalCode']
        }

        # 保存新地址到本地 JSON 文件
        addresses = load_data_from_json('addresses.json')
        addresses.append(address_data)
        with open('addresses.json', 'w', encoding='utf-8') as file:
            json.dump(addresses, file, ensure_ascii=False, indent=4)

        return redirect(url_for('manage_addresses'))

    addresses = load_data_from_json('addresses.json')
    return render_template('addresses.html', addresses=addresses)

if __name__ == '__main__':
    app.run(debug=True)
