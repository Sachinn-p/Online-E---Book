from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import db, Product, CartItem

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:wins10@localhost:5432/shoppingdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret'  

db.init_app(app)
jwt = JWTManager(app)

@app.route('/products', methods=['POST'])
def add_product():
    data = request.json
    p = Product(name=data['name'], price=data['price'])
    db.session.add(p)
    db.session.commit()
    return jsonify({'id': p.id, 'name': p.name, 'price': p.price}), 201

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{'id': x.id, 'name': x.name, 'price': x.price} for x in products])

@app.route('/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.json
    c = CartItem(user_id=user_id, product_id=data['product_id'], quantity=data.get('quantity',1))
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id, 'product_id': c.product_id, 'quantity': c.quantity}), 201

@app.route('/cart', methods=['GET'])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    items = CartItem.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            'id': i.id,
            'product': {'id': i.product.id, 'name': i.product.name, 'price': i.product.price},
            'quantity': i.quantity
        } for i in items
    ])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5001, debug=True)