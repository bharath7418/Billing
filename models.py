
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_manager, UserMixin, login_user, login_required, current_user,  logout_user
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
class ShopDealer(UserMixin,db.Model) :
    id = db.Column(db.Integer, primary_key=True)
    shop_username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    shop_name = db.Column(db.String(150),nullable=False)
    shop_title = db.Column(db.String(150),nullable=False)
    shop_location = db.Column(db.String(150),nullable=False)
    shop_phone_number = db.Column(db.String(10),nullable=False)
    shop_gst_number = db.Column(db.String(15),default=None)
    
class Product(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=True)
    product_name = db.Column(db.String(100))
    product_id = db.Column(db.String(100), nullable=True)
    product_selling_amount = db.Column(db.Integer)
    product_raw_amount = db.Column(db.Integer,nullable=True) 
    backup_product_selling_amount = db.Column(db.Integer, nullable=True,default=None)  # New field to store the original selling amount for discount restoration
    backup_product_raw_amount = db.Column(db.Integer, default=None,nullable=True)  # New field to store the original raw amount for discount restoration
    discount = db.Column(db.Integer,nullable=True)
    product_location = db.Column(db.String(100),nullable=True,default=None)
    product_entry_date = db.Column(db.String(100),nullable=True)
    product_exit_date = db.Column(db.DateTime, default=None,nullable=True)
    customer_phone_number = db.Column(db.String(10), db.ForeignKey('customer.customer_phone_number'), default=None, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, sold, expired, etc.
    def __init__(self, **kwargs):
        super(Product, self).__init__(**kwargs)
        # Automatically sync backups if they aren't explicitly provided
        if self.backup_product_selling_amount is None:
            self.backup_product_selling_amount = self.product_selling_amount
        if self.backup_product_raw_amount is None:
            self.backup_product_raw_amount = self.product_raw_amount
   
class SelledProduct(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=True)
    selled_product_name = db.Column(db.String(100))
    selled_product_id = db.Column(db.String(100))
    selled_product_amount = db.Column(db.Integer)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
 
class Customer(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_phone_number = db.Column(db.String(10),unique=True)
    customer_address = db.Column(db.String(200))
    __tablename__ = 'customer'
    
class Billing(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    customer_no = db.Column(db.String(10))
    customer_name = db.Column(db.String(100))
    customer_address = db.Column(db.String(100), nullable=True)
    billing_amount = db.Column(db.Integer)
    manual_discount = db.Column(db.Integer, default=0)
    grant_total = db.Column(db.Integer)
    applies_discount_amount = db.Column(db.Integer, default=0)
    overall_discount_amount = db.Column(
        db.Integer,
        db.Computed("billing_amount - applies_discount_amount")
    )
    total_quantity = db.Column(db.Integer)
    billing_date = db.Column(db.DateTime, default=datetime.utcnow)
    billing_products = db.relationship('SelledProduct', backref='billing', lazy=True)
