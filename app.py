from flask import Flask, render_template, redirect, session, request,url_for, flash, abort, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_manager,  login_user, login_required, current_user, UserMixin, logout_user
import os
from datetime import date, datetime
from flask_migrate import Migrate
import pandas as pd
from sympy import prod


app  = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pro_secret_key_99')

raw_db_url = os.getenv('DATABASE_URL')
use_tmp_sqlite = os.getenv('VERCEL') == '1'
if raw_db_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url.replace("postgres://", "postgresql://", 1)
elif use_tmp_sqlite:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'home'


#Migrate Procedure
migrate = Migrate(app, db)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
class ShopDealer(UserMixin,db.Model) :
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Product(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    product_name = db.Column(db.String(100))
    product_id = db.Column(db.String(100))
    product_selling_amount = db.Column(db.Integer)
    product_raw_amount = db.Column(db.Integer)  
    product_percentage = db.Column(db.Integer)
    discount = db.Column(db.Integer)
    product_location = db.Column(db.String(100))
    product_entry_date = db.Column(db.String(100))
    product_exit_date = db.Column(db.DateTime, default=None)
    Customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), default=None)
    status = db.Column(db.String(20), default='active')  # active, sold, expired, etc.
  
class SelledProduct(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    selled_product_name = db.Column(db.String(100))
    selled_product_id = db.Column(db.String(100))
    selled_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
 
class Customer(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_id = db.Column(db.String(100))
    customer_phone_number = db.Column(db.String(10))
    customer_address = db.Column(db.String(200))
    
class Billing(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    customer_no = db.Column(db.String(10))
    customer_name = db.Column(db.String(100))
    product_id = db.Column(db.String(100),db.ForeignKey('product.product_id'))
    product_name = db.Column(db.String(100))
    product_amount = db.Column(db.Integer)
    product_quantity = db.Column(db.Integer)
    billing_amount = db.Column(db.Integer)
    total_quantity = db.Column(db.Integer)
    billing_date = db.Column(db.DateTime, default=datetime.utcnow)
    
@login_manager.user_loader
def load_user(user_id):
    # Flask-Login sessions store IDs as strings, so we convert to int
    uid = int(user_id)
    
    user = User.query.get(uid)
    if user:
        return user

    shop_dealer = ShopDealer.query.get(uid)
    if shop_dealer:
        return shop_dealer
    return None

@app.route('/')
def welcome():
    logout_user()
    return render_template('welcome.html')

@app.route('/shop_login',methods=['GET','POST'])
def shop_login():
    if request.method == 'POST':
        shop_name = request.form.get('shop_name')
        password = request.form.get('password')
        shop_dealer = ShopDealer.query.filter_by(shop_name=shop_name).first()
        if shop_dealer and shop_dealer.password == password:
            login_user(shop_dealer)
            return redirect(url_for('shop_dashboard'))
        else:
            flash('Invalid shop name or password', 'danger')
    
    return render_template('shop_login.html')


@app.route('/shop_dashboard')
@login_required
def shop_dashboard():
    return render_template('shop_dashboard.html')

@app.route('/new_product', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        product_id = request.form.get('product_id')
        product_selling_amount = request.form.get('product_selling_amount')
        product_raw_amount = request.form.get('product_raw_amount')
        product_percentage = request.form.get('product_percentage')
        discount = request.form.get('discount')
        status = request.form.get('status')
        product_location = request.form.get('product_location')
        product_entry_date = datetime.utcnow()

        product = Product(
            product_name=product_name,
            product_id=product_id,
            product_selling_amount=product_selling_amount,
            product_raw_amount=product_raw_amount,
            product_percentage=product_percentage,
            discount=discount,
            status=status,
            product_location=product_location,
            product_entry_date=product_entry_date
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully', 'success')
        return redirect(url_for('shop_dashboard'))

    return render_template('new_product.html')

@app.route('/new_billing', methods=['GET', 'POST'])
@login_required
def new_billing():
    bill = Billing.query.all()
    selled_products = SelledProduct.query.order_by(SelledProduct.scanned_at.desc()).all()
    products = Product.query.filter_by(status='scanned').all()
    if request.method == 'POST':
        customer_no = request.form.get('customer_no')
        customer_name = request.form.get('customer_name')
        product_id = request.form.get('product_id')
        product_name = request.form.get('product_name')
        product_amount = request.form.get('product_amount')
        product_quantity = request.form.get('product_quantity')
        billing_amount = request.form.get('billing_amount')
        total_quantity = request.form.get('total_quantity')

        billing = Billing(
            customer_no=customer_no,
            customer_name=customer_name,
            product_id=product_id,
            product_name=product_name,
            product_amount=product_amount,
            product_quantity=product_quantity,
            billing_amount=billing_amount,
            total_quantity=total_quantity
        )
        db.session.add(billing)
        db.session.commit()
        flash('Billing added successfully', 'success')
        return redirect(url_for('new_billing'))
    return render_template('new_billing.html', bill=bill, selled_products=selled_products, products=products)



@app.route('/verify_id', methods=['POST'])
def verify_id():
    Product_id = request.form.get('product_id')
    
    # 1. Check if the ID was actually provided
    if not Product_id:
        flash("Please enter a Product ID to verify.", "warning")
        return redirect(url_for('new_billing'))
        
    # 2. Query the database for the letter
    product = Product.query.filter_by(id=Product_id).first()
    
    # 3. Check if the letter exists and if it is 'Approved'
    if not product or product.status != 'active':
        # If it exists but is already complete, give a specific message
        if product and product.status == 'scanned':
            flash(f"Already Scanned Completed {product.id}", "warning")
        else:
            flash("Invalid Product ID or not approved.", "error")
        return redirect(url_for('new_billing'))
    
    # 4. Process the valid, approved letter
    product.status = 'scanned'  # Mark as scanned/used
    add_product = SelledProduct(
        selled_product_name=product.product_name,
        selled_product_id=product.id,
        selled_customer_id=product.Customer_id
    )
    db.session.add(add_product)
    db.session.commit()
    
    flash(f"Product ID {product.id} verified and marked as scanned!", "success")
    return redirect(url_for('new_billing'))

@app.route('/search_contact', methods=['GET', 'POST'])
def search_contact():
    if request.method == 'POST':
        customer_no = request.form.get('customer_no')
        if not customer_no:
            flash("Please enter a Customer Number to search.", "warning")
            return redirect(url_for('search_contact'))
        
        customer = Customer.query.filter_by(customer_no=customer_no).first()
        if not customer:
            flash(f"No customer found with Number: {customer_no}", "error")
            return redirect(url_for('search_contact'))
        
        return render_template('customer_details.html', customer=customer)
    
    return redirect(url_for('new_billing'))  # Redirect to billing page if accessed via GET

# ==============================
# Bulk Upload Route
# ==============================
# --- Helper for File Validation ---
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Route for Products File Upload & Processing ---
@app.route('/upload_products', methods=['GET', 'POST'])
def upload_products():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            try:
                # Force specific columns to be read as strings to preserve formatting
                string_columns = ['product_name', 'product_id', 'product_selling_amount', 'product_raw_amount', 'product_percentage', 'discount', 'product_location', 'product_entry_date', 'product_exit_date']
                converters = {col: str for col in string_columns}
                
                # Parse based on file type
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                # Clean header spacing
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                products_to_add = []
                duplicate_errors = []
                
                # Iterate rows and extract data
                for index, row in df.iterrows():
                    product_name_val = str(row.get('product_name', '')).strip() if row.get('product_name') else None
                    product_id_val = str(row.get('product_id', '')).strip() if row.get('product_id') else None
                    product_selling_amount_val = row.get('product_selling_amount')  
                    product_raw_amount_val = row.get('product_raw_amount')
                    product_percentage_val = row.get('product_percentage')
                    discount_val = row.get('discount')
                    product_location_val = str(row.get('product_location', '')).strip() if row.get('product_location') else None
                    product_entry_date_val = row.get('product_entry_date')
                    product_exit_date_val = row.get('product_exit_date')
                    # Validate required constraints
                    if not product_name_val or not product_id_val:
                        continue # Skip bad/empty rows
                        
                    # Check for unique product_id constraint violation
                    existing = Product.query.filter_by(product_id=product_id_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Product ID '{product_id_val}' already exists. Skipped.")
                        continue
                    
                    product = Product(
                        product_name=product_name_val,
                        product_id=product_id_val,
                        product_selling_amount=product_selling_amount_val,
                        product_raw_amount=product_raw_amount_val,
                        product_percentage=product_percentage_val,
                        discount=discount_val,
                        product_location=product_location_val,
                        product_entry_date=product_entry_date_val,
                        product_exit_date=product_exit_date_val
                    )
                    products_to_add.append(product)
                
                # Commit valid rows dynamically
                if products_to_add:
                    db.session.bulk_save_objects(products_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(products_to_add)} Product records!', 'success') 
                    
                    products_to_add.append(product)
                
                # Commit valid rows dynamically
                if products_to_add:
                    db.session.bulk_save_objects(products_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(products_to_add)} Product records!', 'success')
                
                if duplicate_errors:
                    for err in duplicate_errors:
                        flash(err, 'warning')
                        
                return redirect(url_for('shop_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error parsing file: {str(e)}", 'danger')
                return redirect(request.url)
                
        else:
            flash('Invalid format! Please use a valid .csv, .xlsx, or .xls file.', 'danger')
            return redirect(request.url)
            
    return render_template('products_bulk_import.html')




@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('welcome'))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='admin')
        db.session.add(admin_user)
        db.session.commit()
    if not ShopDealer.query.filter_by(shop_name='admin_shop').first():
        admin_shop = ShopDealer(shop_name='admin_shop', password='admin')
        db.session.add(admin_shop)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)

