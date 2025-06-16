from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
import csv
import phonenumbers
from phonenumbers import NumberParseException
import io
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
# Use environment variable for secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'contactcleaner-secret-key-change-in-production')

# Configuration
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed columns for cleaning
ALLOWED_COLUMNS = ["First Name", "Last Name", "Title", "Company", "Email", "Phone Number", "Location"]

def normalize_phone_number(phone_str, default_country='US'):
    """Normalize phone number to E.164 format"""
    try:
        # Convert to string and handle various null/empty cases
        phone_str_clean = str(phone_str).strip()
        if not phone_str_clean or phone_str_clean in ['', 'None', 'NULL', 'nan']:
            return ''
        
        # Clean up the phone string first
        phone_clean = phone_str_clean.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        if not phone_clean:
            return phone_str_clean
            
        # Add back + if it was there originally
        if phone_str_clean.startswith('+'):
            phone_clean = '+' + phone_clean
            
        # Parse the phone number
        parsed = phonenumbers.parse(phone_clean, default_country)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        else:
            return phone_str_clean  # Return original if invalid
    except (NumberParseException, ValueError, TypeError):
        return str(phone_str) if phone_str is not None else ''

def get_phone_columns(headers):
    """Get all phone-related columns from the headers"""
    phone_columns = []
    for col in headers:
        if any(keyword in col.lower() for keyword in ['phone', 'mobile', 'cell', 'tel']):
            phone_columns.append(col)
    return phone_columns

def create_phone_number_column(data, headers):
    """Create a unified Phone Number column from various phone columns"""
    phone_cols = get_phone_columns(headers)
    if not phone_cols:
        return data, headers
    
    # Add Phone Number column if it doesn't exist
    if 'Phone Number' not in headers:
        headers.append('Phone Number')
        phone_idx = len(headers) - 1
        
        # Add empty phone number to existing rows
        for row in data:
            while len(row) <= phone_idx:
                row.append('')
    else:
        phone_idx = headers.index('Phone Number')
    
    # Fill Phone Number column
    for row in data:
        if phone_idx >= len(row):
            row.extend([''] * (phone_idx - len(row) + 1))
            
        for col in phone_cols:
            if col in headers:
                col_idx = headers.index(col)
                if col_idx < len(row):
                    phone_val = str(row[col_idx]).strip()
                    if phone_val and phone_val not in ['', 'None', 'NULL', 'nan']:
                        row[phone_idx] = phone_val
                        break
    
    return data, headers

def create_location_column(data, headers):
    """Create a unified Location column from City, State, Country"""
    location_cols = ['City', 'State', 'Country']
    available_location_cols = [col for col in location_cols if col in headers]
    
    if not available_location_cols:
        return data, headers
    
    # Add Location column if it doesn't exist
    if 'Location' not in headers:
        headers.append('Location')
        location_idx = len(headers) - 1
        
        # Add empty location to existing rows
        for row in data:
            while len(row) <= location_idx:
                row.append('')
    else:
        location_idx = headers.index('Location')
    
    # Fill Location column
    for row in data:
        if location_idx >= len(row):
            row.extend([''] * (location_idx - len(row) + 1))
            
        parts = []
        for col in location_cols:
            if col in headers:
                col_idx = headers.index(col)
                if col_idx < len(row):
                    location_val = str(row[col_idx]).strip()
                    if location_val and location_val not in ['', 'None', 'NULL', 'nan']:
                        parts.append(location_val)
        
        row[location_idx] = ', '.join(parts) if parts else ''
    
    return data, headers

def clean_csv_data(data, headers, cleaning_options):
    """Apply selected cleaning operations to the CSV data"""
    # Create unified columns first
    data, headers = create_phone_number_column(data, headers)
    data, headers = create_location_column(data, headers)
    
    # Trim whitespace in all string columns
    if 'trim_whitespace' in cleaning_options:
        for row in data:
            for i, cell in enumerate(row):
                row[i] = str(cell).strip()
    
    # Drop rows with missing First Name or Last Name
    if 'drop_missing_names' in cleaning_options:
        if 'First Name' in headers and 'Last Name' in headers:
            first_name_idx = headers.index('First Name')
            last_name_idx = headers.index('Last Name')
            
            filtered_data = []
            for row in data:
                if (first_name_idx < len(row) and last_name_idx < len(row) and
                    str(row[first_name_idx]).strip() and str(row[last_name_idx]).strip() and
                    str(row[first_name_idx]).strip() not in ['', 'None', 'NULL', 'nan'] and
                    str(row[last_name_idx]).strip() not in ['', 'None', 'NULL', 'nan']):
                    filtered_data.append(row)
            data = filtered_data
    
    # Standardize Title to title-case
    if 'standardize_title' in cleaning_options and 'Title' in headers:
        title_idx = headers.index('Title')
        for row in data:
            if title_idx < len(row):
                title_val = str(row[title_idx]).strip()
                if title_val and title_val not in ['', 'None', 'NULL', 'nan']:
                    row[title_idx] = title_val.title()
    
    # Remove duplicates based on Email
    if 'remove_email_duplicates' in cleaning_options and 'Email' in headers:
        email_idx = headers.index('Email')
        seen_emails = set()
        filtered_data = []
        
        for row in data:
            if email_idx < len(row):
                email = str(row[email_idx]).strip().lower()
                if email and email not in ['', 'none', 'null', 'nan'] and email not in seen_emails:
                    seen_emails.add(email)
                    filtered_data.append(row)
        data = filtered_data
    
    # Remove duplicates based on Phone Number
    if 'remove_phone_duplicates' in cleaning_options and 'Phone Number' in headers:
        phone_idx = headers.index('Phone Number')
        seen_phones = set()
        filtered_data = []
        
        for row in data:
            if phone_idx < len(row):
                phone = str(row[phone_idx]).strip()
                if phone and phone not in ['', 'None', 'NULL', 'nan'] and phone not in seen_phones:
                    seen_phones.add(phone)
                    filtered_data.append(row)
        data = filtered_data
    
    # Normalize phone numbers
    if 'normalize_phones' in cleaning_options and 'Phone Number' in headers:
        phone_idx = headers.index('Phone Number')
        for row in data:
            if phone_idx < len(row):
                row[phone_idx] = normalize_phone_number(row[phone_idx])
    
    # Lowercase email addresses
    if 'lowercase_emails' in cleaning_options and 'Email' in headers:
        email_idx = headers.index('Email')
        for row in data:
            if email_idx < len(row):
                email_val = str(row[email_idx]).strip()
                if email_val and email_val not in ['', 'None', 'NULL', 'nan']:
                    row[email_idx] = email_val.lower()
    
    # Keep only allowed columns
    if 'filter_columns' in cleaning_options:
        available_allowed_cols = [col for col in ALLOWED_COLUMNS if col in headers]
        if available_allowed_cols:
            # Get indices of allowed columns
            allowed_indices = [headers.index(col) for col in available_allowed_cols]
            
            # Filter headers
            headers = available_allowed_cols
            
            # Filter data
            filtered_data = []
            for row in data:
                filtered_row = []
                for idx in allowed_indices:
                    if idx < len(row):
                        filtered_row.append(row[idx])
                    else:
                        filtered_row.append('')
                filtered_data.append(filtered_row)
            data = filtered_data
    
    return data, headers

def read_csv_file(file_path):
    """Read CSV file and return data and headers"""
    data = []
    headers = []
    
    try:
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as csvfile:
                    # Detect delimiter
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.reader(csvfile, delimiter=delimiter)
                    headers = next(reader, [])
                    data = [row for row in reader]
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Clean empty rows
        data = [row for row in data if any(cell.strip() for cell in row)]
        
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
    return data, headers

def csv_to_dict_list(data, headers):
    """Convert CSV data to list of dictionaries for template rendering"""
    dict_list = []
    for row in data:
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(row):
                row_dict[header] = row[i]
            else:
                row_dict[header] = ''
        dict_list.append(row_dict)
    return dict_list

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.csv'):
            try:
                # Save uploaded file temporarily
                session_id = str(uuid.uuid4())
                filename = secure_filename(f"{session_id}.csv")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Read CSV data
                data, headers = read_csv_file(filepath)
                
                if not data or not headers:
                    flash('The uploaded CSV file is empty or invalid', 'error')
                    return redirect(request.url)
                
                # Store file info in session
                session['current_file'] = filepath
                session['original_shape'] = (len(data), len(headers))
                session['filename'] = file.filename
                
                # Convert to dict format for template
                preview_data = csv_to_dict_list(data[:10], headers)
                
                return render_template('index.html', 
                                     uploaded=True, 
                                     preview_df=preview_data,
                                     original_shape=(len(data), len(headers)),
                                     columns=headers,
                                     filename=file.filename)
                
            except Exception as e:
                flash(f'Error reading CSV file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Please upload a CSV file', 'error')
            return redirect(request.url)
    
    return render_template('index.html', uploaded=False)

@app.route('/clean', methods=['POST'])
def clean_data():
    if 'current_file' not in session:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))
    
    try:
        # Load the original CSV data
        data, headers = read_csv_file(session['current_file'])
        
        # Get selected cleaning options
        cleaning_options = request.form.getlist('cleaning_options')
        
        if not cleaning_options:
            flash('Please select at least one cleaning option', 'warning')
            preview_data = csv_to_dict_list(data[:10], headers)
            return render_template('index.html', 
                                 uploaded=True,
                                 preview_df=preview_data,
                                 original_shape=session['original_shape'],
                                 columns=headers,
                                 filename=session.get('filename', 'unknown'))
        
        # Apply cleaning
        cleaned_data, cleaned_headers = clean_csv_data(data, headers, cleaning_options)
        
        # Save cleaned data
        session_id = str(uuid.uuid4())
        cleaned_filename = secure_filename(f"{session_id}_cleaned.csv")
        cleaned_filepath = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
        
        with open(cleaned_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(cleaned_headers)
            writer.writerows(cleaned_data)
        
        session['cleaned_file'] = cleaned_filepath
        session['cleaned_shape'] = (len(cleaned_data), len(cleaned_headers))
        session['cleaning_applied'] = cleaning_options
        
        # Convert to dict format for template
        preview_data = csv_to_dict_list(cleaned_data[:10], cleaned_headers)
        
        return render_template('index.html', 
                             uploaded=True,
                             cleaned=True,
                             preview_df=preview_data,
                             original_shape=session['original_shape'],
                             cleaned_shape=(len(cleaned_data), len(cleaned_headers)),
                             columns=cleaned_headers,
                             filename=session.get('filename', 'unknown'),
                             cleaning_applied=cleaning_options)
        
    except Exception as e:
        flash(f'Error cleaning data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download')
def download_csv():
    if 'cleaned_file' not in session:
        flash('No cleaned data available', 'error')
        return redirect(url_for('index'))
    
    try:
        return send_file(session['cleaned_file'], 
                        as_attachment=True, 
                        download_name='cleaned_contacts.csv',
                        mimetype='text/csv')
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/reset')
def reset():
    # Clean up session files
    if 'current_file' in session:
        try:
            if os.path.exists(session['current_file']):
                os.remove(session['current_file'])
        except:
            pass
    if 'cleaned_file' in session:
        try:
            if os.path.exists(session['cleaned_file']):
                os.remove(session['cleaned_file'])
        except:
            pass
    
    session.clear()
    return redirect(url_for('index'))

# Cleanup function to remove old temp files
def cleanup_old_files():
    """Remove temp files older than 1 hour"""
    try:
        import time
        current_time = time.time()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getctime(filepath)
                if file_age > 3600:  # 1 hour
                    os.remove(filepath)
    except:
        pass

if __name__ == '__main__':
    # Clean up old files on startup
    cleanup_old_files()
    
    # Production vs Development settings
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(debug=debug, host='0.0.0.0', port=port) 