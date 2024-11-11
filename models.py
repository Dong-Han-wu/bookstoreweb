from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'

    uid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price = db.Column(db.Float)
    salePrice = db.Column(db.Float)
    description = db.Column(db.Text)
    owner = db.Column(db.String(100))
    tags = db.Column(db.String(200))

    def __repr__(self):
        return f"<Product {self.name}>"
