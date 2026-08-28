from flask import Flask, render_template, redirect, request,url_for, flash, abort, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_manager,  login_user, login_required, current_user, UserMixin, logout_user
import os
import qrcode
import io
import base64
from datetime import date, datetime, time
from flask_migrate import Migrate
import pandas as pd
import requests
from sqlalchemy import func


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
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=True,default=0)
    product_name = db.Column(db.String(100))
    product_id = db.Column(db.String(100))
    product_selling_amount = db.Column(db.Integer)
    product_raw_amount = db.Column(db.Integer) 
    backup_product_selling_amount = db.Column(db.Integer, default=None)  # New field to store the original selling amount for discount restoration
    backup_product_raw_amount = db.Column(db.Integer, default=None)  # New field to store the original raw amount for discount restoration
    discount = db.Column(db.Integer)
    product_location = db.Column(db.String(100))
    product_entry_date = db.Column(db.String(100))
    product_exit_date = db.Column(db.DateTime, default=None)
    customer_phone_number = db.Column(db.String(10), db.ForeignKey('customer.customer_phone_number'), default=None)
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
    applies_discount = db.Column(db.Integer, default=0)  # New field to indicate if a discount was applied
    applies_discount_amount = db.Column(db.Integer, default=0)
    total_quantity = db.Column(db.Integer)
    billing_date = db.Column(db.DateTime, default=datetime.utcnow)
    billing_products = db.relationship('SelledProduct', backref='billing', lazy=True)
              
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

# @app.route('/shop_dashboard')
# @login_required
@app.route('/shop_dashboard')
def shop_dashboard():
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    
    # 1. Daily Billing Count
    daily_billing_count = Billing.query.filter(Billing.billing_date >= today_start).count()
    
    # 2. Overall Total Bill Amount
    total_bill_amount = db.session.query(func.sum(Billing.billing_amount)).scalar() or 0
    
    # 3. Total Customers Count
    total_customers = Customer.query.count()
    
    # 4. Overall Active Product Count
    active_product_count = Product.query.filter_by(status='active').count()

    return render_template('shop_dashboard.html',
                           daily_billing_count=daily_billing_count,
                           total_bill=total_bill_amount,
                           total_customers=total_customers,
                           active_product_count=active_product_count)

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
        product_entry_date = datetime.utcnow().strftime("%Y-%m-%d")
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
    products = Product.query.all()
    last_bill = Billing.query.order_by(Billing.id.desc()).first()
    # If bills exist, add 1. If the table is empty, start at 1.
    next_bill_no = (last_bill.id + 1) if last_bill else 1
    selled_products = SelledProduct.query.order_by(SelledProduct.scanned_at.desc()).all()
    products = Product.query.filter_by(status='scanned').all()
    
    if request.method == 'POST':
        customer_no = request.form.get('customer_phone_number')
        customer_name = request.form.get('customer_name')
        customer_address = request.form.get('customer_address')
        total_selling_count = request.form.get('total_selling_count')
        total_selling_amount = request.form.get('total_selling_amount')
        manual_percentage = request.form.get('manual-percentage')
        
        customer = Customer.query.filter_by(customer_phone_number=customer_no).first()
        if not customer:
            customer = Customer(
                customer_name=customer_name,
                customer_phone_number=customer_no,
                customer_address=customer_address)
            db.session.add(customer)
            db.session.commit()
        
        billing = Billing(
            customer_no=customer_no,
            customer_name=customer_name,
            customer_address = customer_address,
            total_quantity=total_selling_count,
            billing_amount = total_selling_amount,
            applies_discount = manual_percentage,
            applies_discount_amount = int(total_selling_amount) - (int(total_selling_amount) * int(manual_percentage) / 100) if manual_percentage else int(total_selling_amount)
            
        )
        
        db.session.add(billing)
        db.session.commit()
        
        
        now_selled = Product.query.filter_by(status='scanned').all()
        
        for now in now_selled:
            selled_product = SelledProduct.query.filter_by(selled_product_id=now.id).first()
            if selled_product:
                selled_product.billing_id = billing.id
                selled_product.selled_product_amount = now.product_selling_amount
        db.session.commit()
        
        for product in products:
            product.status = 'sold'
            product.product_exit_date = datetime.utcnow()
            product.customer_phone_number = customer_no
            product.billing_id = billing.id
        db.session.commit()
        
        send_whatsapp_bill(
            customer_no,
            customer_name,
            billing
        )
        
        
        return redirect(url_for('bill_show_page', billing_id=next_bill_no))
        
    return render_template('new_billing.html',
        selled_products=selled_products, 
        products=products,
        customer_no='', 
        customer_name='', 
        customer_address='',
        next_bill_no=next_bill_no
    )

@app.route('/bill_show_page/<int:billing_id>')
def bill_show_page(billing_id):
    billing = Billing.query.get_or_404(billing_id)
    selled = SelledProduct.query.filter_by(billing_id=billing_id)
    shop = ShopDealer.query.all()
    products = Product.query.filter_by(billing_id=billing_id)
    return render_template('bill_show_page.html', billing=billing,selled=selled,shop=shop,products=products)

@app.route('/whatsapp_bill/<int:billing_id>')
def whatsapp_bill(billing_id):
    billing = Billing.query.get_or_404(billing_id)
    send_whatsapp_bill(
        billing.customer_no,
        billing.customer_name
    )
    flash("WhatsApp bill sent successfully!", "success")
    return redirect(url_for('bill_show_page', billing_id=billing.id))

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
    )
    db.session.add(add_product)
    db.session.commit()
    
    flash(f"Product ID {product.id} verified and marked as scanned!", "success")
    return redirect(url_for('new_billing'))

@app.route('/discount_apply/<int:id>')
def apply_discount(id):
    product = Product.query.get_or_404(id)
    
    if product.discount and product.discount > 0:
        discount_percentage = product.discount
        discount_value = (product.product_selling_amount * discount_percentage) / 100
        
        # 3. Reduce the selling amount value
        product.product_selling_amount = int(product.product_selling_amount - discount_value)
        
        db.session.commit()
        flash(f"Successfully reduced price by {discount_percentage}%!", "success")
    else:
        flash("Discount already applied or invalid.", "warning")
        
    return redirect(url_for('new_billing'))

@app.route('/discount_remove/<int:id>')
def remove_discount(id):
    product = Product.query.get_or_404(id)
    product.product_selling_amount = product.backup_product_selling_amount
    db.session.commit()
    flash("Discount removed and original price restored!", "success")
    return redirect(url_for('new_billing'))

@app.route('/clear_product/<int:id>')
def clear_product(id):
    product = Product.query.get_or_404(id)
    selled = SelledProduct.query.filter_by(selled_product_id=product.id).first()
    if selled:
        db.session.delete(selled)
    product.product_selling_amount = product.backup_product_selling_amount
    product.status= 'active'
    db.session.commit()
    product_name = product.product_name
    flash(f"Removed the {product_name} !", "success")
    return redirect(url_for('new_billing'))


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
                    
                    clean_val = str(val).strip()
                    
                    try:
                        # Handles typical pandas string conversions (YYYY-MM-DD HH:MM:SS)
                        return datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        try:
                            # Fallback for shorthand dates "YYYY-MM-DD"
                            return datetime.strptime(clean_val, "%Y-%m-%d").date()
                        except ValueError:
                            return None

                # Iterate rows and extract data
                for index, row in df.iterrows():
                    product_name_val = str(row.get('product_name', '')).strip() if row.get('product_name') else None
                    product_id_val = str(row.get('product_id', '')).strip() if row.get('product_id') else None
                    
                    # Numeric conversions (handle potential string or NaNR states gracefully)
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
                        
                    
                    # 3. Map sheet values to your exact model keywords
                    client = Customer(
                        customer_name=client_name_val,
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

def generate_qr_base64(data):
    """Helper function to convert string data into a Base64-encoded QR image."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,  # Slightly smaller box size fits better on grid layouts
        border=3,
    )
    qr.add_data(str(data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.route("/qr_code_page", methods=["GET"])
def qr_code_page():
    products = Product.query.all()
    shop = ShopDealer.query.all()

    # Build a list of dictionaries containing the product and its generated QR code
    qr_list = []
    for product in products:
        qr_base64 = generate_qr_base64(product.product_id)
        qr_list.append({"product": product, "qr_code": qr_base64})

    return render_template("qr_code.html", qr_list=qr_list,shop=shop)


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


def send_whatsapp_bill(phone, customer_name, billing):
    webhook_url = "https://YOUR-N8N-DOMAIN/webhook/send-bill"

    products = []

    for item in billing.billing_products:
        products.append({
            "name": item.selled_product_name,
            "price": item.selled_product_amount
        })

    payload = {
        "phone": phone,
        "customer_name": customer_name,
        "bill_no": billing.id,
        "total_quantity": billing.total_quantity,
        "total_amount": billing.billing_amount,
        "products": products
    }

    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    app.run(debug=True)

