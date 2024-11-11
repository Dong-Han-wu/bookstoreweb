import json
from flask import Flask, jsonify, request, render_template
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import os

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化 Firebase
cred = credentials.Certificate("serviceAccountKey.json")  # 使用 Firebase 的凭证文件
initialize_app(cred)
db = firestore.client()

# Firestore 集合引用
users_ref = db.collection('users')
orders_ref = db.collection('orders')
products_ref = db.collection('products')


# 读取 product.json 文件的函数
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

# 获取所有产品信息 API
@app.route('/products', methods=['GET', 'POST'])
def manage_products():
    if request.method == 'POST':
        # Create a new product (unchanged logic from original code)
        product_data = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'salePrice': float(request.form['salePrice']),
            'category': request.form['category'],
            'createdTime': datetime.datetime.now(),
            'owner': request.form['owner'],
            'tags': request.form.getlist('tags')
        }
        db.collection('products').add(product_data)
        return redirect(url_for('manage_products'))

    # Load products from JSON file
    products = load_products_from_json()

    # Handle potential errors during JSON loading
    if not products:
        # Optional: Provide a user-friendly error message or default data
        flash("Error: Could not load product data. Please check the file or provide default data.")
        products = []  # Or create default product data (optional)

    return jsonify(products), 200

# 根路由 - 渲染网页
@app.route('/')
def index():
    return render_template('index.html')


# 用户 API
@app.route('/users', methods=['GET'])
def get_all_users():
    try:
        all_users = [doc.to_dict() for doc in users_ref.stream()]
        return jsonify(all_users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 获取所有订单信息 API
@app.route('/orders', methods=['GET'])
def get_all_orders():
    try:
        all_orders = [doc.to_dict() for doc in orders_ref.stream()]
        return jsonify(all_orders), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 启动应用
if __name__ == '__main__':
    app.run(debug=True)
