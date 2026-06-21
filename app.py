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
    shop_username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    shop_name = db.Column(db.String(150),nullable=False)
    shop_title = db.Column(db.String(150),nullable=False)
    shop_location = db.Column(db.String(150),nullable=False)
    shop_phone_number = db.Column(db.String(10),nullable=False)
    shop_gst_number = db.Column(db.String(15),default=None)
    
    
    
class Product(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    product_name = db.Column(db.String(100))
    product_id = db.Column(db.String(100))
    product_selling_amount = db.Column(db.Integer)
    product_raw_amount = db.Column(db.Integer)  
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
    selled_product_amount = db.Column(db.Integer)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
 
class Customer(db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_id = db.Column(db.String(100))
    customer_phone_number = db.Column(db.String(10))
    customer_address = db.Column(db.String(200))
    __tablename__ = 'customer'
    
    
    
    
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
        shop_username = request.form.get('shop_username')
        password = request.form.get('password')
        shop_dealer = ShopDealer.query.filter_by(shop_username=shop_username).first()
        if shop_dealer and shop_dealer.password == password:
            login_user(shop_dealer)
            return redirect(url_for('shop_dashboard'))
        else:
            flash('Invalid shop username or password', 'danger')
    
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
        discount = request.form.get('discount')
        status = request.form.get('status')
        product_location = request.form.get('product_location')
        product_entry_date = datetime.utcnow()

        product = Product(
            product_name=product_name,
            product_id=product_id,
            product_selling_amount=product_selling_amount,
            product_raw_amount=product_raw_amount,
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

@app.route('/search_contact/<customer_no>', methods=['GET'])
@login_required
def search_contact(customer_no):
    customer = Customer.query.filter_by(customer_phone_number=customer_no).first()
    if not customer:
        return jsonify({"success": False, "message": "Customer not found"}), 404
        
    return jsonify({
        "success": True,
        "customer_name": customer.customer_name,
        "customer_address": customer.customer_address
    })

@app.route('/new_billing', methods=['GET', 'POST'])
@login_required
def new_billing():
    bill = Billing.query.all()
    selled_products = SelledProduct.query.order_by(SelledProduct.scanned_at.desc()).all()
    products = Product.query.filter_by(status='scanned').all()
    
    if request.method == 'POST':
        # Extract values from form submission
        customer_no = request.form.get('customer_no')
        customer_name = request.form.get('customer_name')
        customer_address = request.form.get('customer_address')
        
        billing = Billing(
            customer_no=customer_no,
            customer_name=customer_name,
            customer_address=customer_address
        )
        db.session.add(billing)
        db.session.commit()
        flash('Billing added successfully', 'success')
        return redirect(url_for('new_billing'))
        
    return render_template('new_billing.html',bill=bill, 
        selled_products=selled_products, 
        products=products,
        customer_no='', 
        customer_name='', 
        customer_address=''
    )

@app.route('/customer_page')
@login_required
def customer_page():
    customers = Customer.query.all()
    return render_template('customer_page.html', customers=customers)

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

@app.route('/discount_apply/<int:id>')
def apply_discount(id):
    product = Product.query.get_or_404(id)
    
    if product.discount and product.discount > 0:
        # 1. Back up the current selling amount into raw_amount if it hasn't been done yet
        product.product_raw_amount = product.product_selling_amount
        
        # 2. Calculate the discount value reduction
        discount_percentage = product.discount
        discount_value = (product.product_selling_amount * discount_percentage) / 100
        
        # 3. Reduce the selling amount value
        product.product_selling_amount = int(product.product_selling_amount - discount_value)
        
        # 4. Set discount field to 0 so the "Apply Discount" button hides/deactivates
        product.discount = 0 
        
        db.session.commit()
        flash(f"Successfully reduced price by {discount_percentage}%!", "success")
    else:
        flash("Discount already applied or invalid.", "warning")
        
    return redirect(url_for('new_billing'))

@app.route('/discount_remove/<int:product_id>', methods=['POST'])
def discount_remove(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.product_raw_amount:
        # Calculate percentage back out to restore the original 'discount available' percentage value 
        restored_discount = round(((product.product_raw_amount - product.product_selling_amount) / product.product_raw_amount) * 100)
        
        # Reset original fields values metrics tracking
        product.product_selling_amount = product.product_raw_amount
        product.discount = restored_discount
        product.product_raw_amount = None # Clear structural configuration markers
        
        db.session.commit()
        return jsonify({"success": True, "message": "Product values rolled back cleanly."})
        
    return jsonify({"success": False, "message": "No modification properties tracked on this row entity."}), 400

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
                # Force identifier and names to remain string type to prevent truncation
                string_columns = ['product_name', 'product_id', 'product_location']
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
                
                # Helper function to convert dynamic row text into datetime or None
                def parse_date(val):
                    if not val or str(val).strip().lower() in ['nil', 'none', 'null', '']:
                        return None
                    try:
                        # Handles typical pandas string conversions
                        return datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            # Fallback for shorthand dates "YYYY-MM-DD"
                            return datetime.strptime(str(val).strip(), "%Y-%m-%d")
                        except ValueError:
                            return None

                # Iterate rows and extract data
                for index, row in df.iterrows():
                    product_name_val = str(row.get('product_name', '')).strip() if row.get('product_name') else None
                    product_id_val = str(row.get('product_id', '')).strip() if row.get('product_id') else None
                    
                    # Numeric conversions (handle potential string or NaN states gracefully)
                    product_selling_amount_val = row.get('product_selling_amount')  
                    product_raw_amount_val = row.get('product_raw_amount')
                    discount_val = row.get('discount')
                    product_location_val = str(row.get('product_location', '')).strip() if row.get('product_location') else None
                    
                    # Safely handle the Date Conversions
                    product_entry_date_val = parse_date(row.get('product_entry_date'))
                    product_exit_date_val = parse_date(row.get('product_exit_date'))
                    
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
                        discount=discount_val,
                        product_location=product_location_val,
                        product_entry_date=product_entry_date_val,
                        product_exit_date=product_exit_date_val
                    )
                    products_to_add.append(product)
                
                # Commit valid rows dynamically (Removed the duplicated block)
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

@app.route('/upload_clients', methods=['GET', 'POST'])
def upload_clients():
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
                string_columns = ['client_name', 'client_id', 'client_phone_number', 'client_address']
                converters = {col: str for col in string_columns}
                
                # Parse based on file type
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                # Clean header spacing
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                clients_to_add = []
                duplicate_errors = []
                seen_in_file = set()  # Tracks IDs within the file to prevent internal duplicates
                
                # Iterate rows and extract data
                for index, row in df.iterrows():
                    # 1. Get raw string values from the spreadsheet columns
                    client_name_val = str(row.get('client_name', '')).strip() if row.get('client_name') else None
                    client_id_val = str(row.get('client_id', '')).strip() if row.get('client_id') else None
                    client_phone_number_val = str(row.get('client_phone_number', '')).strip() if row.get('client_phone_number') else None
                    client_address_val = str(row.get('client_address', '')).strip() if row.get('client_address') else None
                    
                    # Validate required fields
                    if not client_name_val or not client_id_val:
                        continue # Skip bad/empty rows
                    
                    # Check for duplicates within the uploaded file itself
                    if client_id_val in seen_in_file:
                        duplicate_errors.append(f"Row {index + 2}: Client ID '{client_id_val}' is duplicated inside the file. Skipped.")
                        continue
                    seen_in_file.add(client_id_val)
                        
                    # 2. Check database using your model's real property name: 'customer_id'
                    existing = Customer.query.filter_by(customer_id=client_id_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Client ID '{client_id_val}' already exists in the system. Skipped.")
                        continue
                    
                    # 3. Map sheet values to your exact model keywords
                    client = Customer(
                        customer_name=client_name_val,
                        customer_id=client_id_val,
                        customer_phone_number=client_phone_number_val,
                        customer_address=client_address_val
                    )
                    clients_to_add.append(client)
                
                # Commit valid rows cleanly exactly once
                if clients_to_add:
                    db.session.bulk_save_objects(clients_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(clients_to_add)} Client records!', 'success')
                
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
            
    return render_template('clients_bulk_import.html')


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
    if not ShopDealer.query.filter_by(shop_name='RAMAJAYAM').first():
        admin_shop = ShopDealer(shop_name='RAMAJAYAM',shop_username='ramajayam',password='ram',shop_title='Tailors & Readymades',shop_location='Bypass Road, Pernamallur.\n Vandavasi Tk, Tiruvannamallai District - 604 503.',shop_phone_number='9364290146')
        db.session.add(admin_shop)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)

