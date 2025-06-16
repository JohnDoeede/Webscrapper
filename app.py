from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
import pandas as pd
import phonenumbers
from phonenumbers import NumberParseException
import io
import os
from werkzeug.utils import secure_filename
import uuid
import tempfile

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
        if not phone_str_clean or phone_str_clean in ['nan', 'NaN', 'None', '<NA>', '']:
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
        return str(phone_str) if phone_str is not None else ''  # Return original if can't parse

def get_phone_columns(df):
    """Get all phone-related columns from the dataframe"""
    phone_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['phone', 'mobile', 'cell', 'tel']):
            phone_columns.append(col)
    return phone_columns

def create_phone_number_column(df):
    """Create a unified Phone Number column from various phone columns"""
    phone_cols = get_phone_columns(df)
    if not phone_cols:
        return df
    
    # Create Phone Number column by taking the first non-empty phone number
    df['Phone Number'] = ''
    for idx, row in df.iterrows():
        for col in phone_cols:
            try:
                phone_val = str(row[col]).strip()
                if phone_val and phone_val not in ['nan', 'NaN', 'None', '<NA>', '']:
                    df.at[idx, 'Phone Number'] = phone_val
                    break
            except (ValueError, TypeError):
                continue
    
    return df

def create_location_column(df):
    """Create a unified Location column from City, State, Country"""
    location_cols = ['City', 'State', 'Country']
    
    if any(col in df.columns for col in location_cols):
        df['Location'] = ''
        for idx, row in df.iterrows():
            parts = []
            for col in location_cols:
                if col in df.columns:
                    try:
                        location_val = str(row[col]).strip()
                        if location_val and location_val not in ['nan', 'NaN', 'None', '<NA>', '']:
                            parts.append(location_val)
                    except (ValueError, TypeError):
                        continue
            df.at[idx, 'Location'] = ', '.join(parts) if parts else ''
    
    return df

def clean_dataframe(df, cleaning_options):
    """Apply selected cleaning operations to the dataframe"""
    df_cleaned = df.copy()
    
    # Create unified columns first
    df_cleaned = create_phone_number_column(df_cleaned)
    df_cleaned = create_location_column(df_cleaned)
    
    # Trim whitespace in all string columns
    if 'trim_whitespace' in cleaning_options:
        for col in df_cleaned.select_dtypes(include=['object']).columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
            # Replace 'nan' strings with empty strings
            df_cleaned[col] = df_cleaned[col].replace('nan', '')
    
    # Drop rows with missing First Name or Last Name
    if 'drop_missing_names' in cleaning_options:
        df_cleaned = df_cleaned.dropna(subset=['First Name', 'Last Name'])
        df_cleaned = df_cleaned[
            (df_cleaned['First Name'].astype(str).str.strip() != '') & 
            (df_cleaned['Last Name'].astype(str).str.strip() != '') &
            (df_cleaned['First Name'].astype(str).str.strip() != 'nan') & 
            (df_cleaned['Last Name'].astype(str).str.strip() != 'nan')
        ]
    
    # Standardize Title to title-case
    if 'standardize_title' in cleaning_options and 'Title' in df_cleaned.columns:
        df_cleaned['Title'] = df_cleaned['Title'].astype(str).str.title()
        df_cleaned['Title'] = df_cleaned['Title'].replace('Nan', '')
    
    # Remove duplicates based on Email
    if 'remove_email_duplicates' in cleaning_options and 'Email' in df_cleaned.columns:
        # Only remove duplicates where email is not empty
        df_cleaned = df_cleaned[df_cleaned['Email'].astype(str).str.strip() != '']
        df_cleaned = df_cleaned.drop_duplicates(subset=['Email'], keep='first')
    
    # Remove duplicates based on Phone Number
    if 'remove_phone_duplicates' in cleaning_options and 'Phone Number' in df_cleaned.columns:
        # Only remove duplicates where phone is not empty
        df_cleaned = df_cleaned[df_cleaned['Phone Number'].astype(str).str.strip() != '']
        df_cleaned = df_cleaned.drop_duplicates(subset=['Phone Number'], keep='first')
    
    # Normalize phone numbers
    if 'normalize_phones' in cleaning_options and 'Phone Number' in df_cleaned.columns:
        df_cleaned['Phone Number'] = df_cleaned['Phone Number'].apply(normalize_phone_number)
    
    # Lowercase email addresses
    if 'lowercase_emails' in cleaning_options and 'Email' in df_cleaned.columns:
        df_cleaned['Email'] = df_cleaned['Email'].astype(str).str.lower()
        df_cleaned['Email'] = df_cleaned['Email'].replace('nan', '')
    
    # Keep only allowed columns
    if 'filter_columns' in cleaning_options:
        available_allowed_cols = [col for col in ALLOWED_COLUMNS if col in df_cleaned.columns]
        if available_allowed_cols:
            df_cleaned = df_cleaned[available_allowed_cols]
    
    return df_cleaned

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
                # Read CSV into DataFrame with better error handling
                try:
                    # First, try reading with string dtype for all columns to avoid type issues
                    df = pd.read_csv(file, dtype=str, keep_default_na=False)
                except Exception:
                    # If that fails, try with default settings but handle encoding
                    file.seek(0)  # Reset file pointer
                    df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
                
                if df.empty:
                    flash('The uploaded CSV file is empty', 'error')
                    return redirect(request.url)
                
                # Clean up the dataframe - replace empty strings with NaN for better processing
                df = df.replace('', pd.NA)
                
                # Convert all columns to string type to avoid float/string mixing issues
                for col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '').replace('<NA>', '')
                
                # Store DataFrame in temp file
                session_id = str(uuid.uuid4())
                filename = secure_filename(f"{session_id}.csv")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                df.to_csv(filepath, index=False)
                
                session['current_file'] = filepath
                session['original_shape'] = df.shape
                session['filename'] = file.filename
                
                # Show preview
                preview_df = df.head(10)
                return render_template('index.html', 
                                     uploaded=True, 
                                     preview_df=preview_df,
                                     original_shape=df.shape,
                                     columns=list(df.columns),
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
        # Load the original DataFrame with consistent data types
        try:
            df = pd.read_csv(session['current_file'], dtype=str, keep_default_na=False)
        except Exception:
            df = pd.read_csv(session['current_file'])
        
        # Clean up the dataframe - ensure consistent string handling
        df = df.replace('', pd.NA)
        for col in df.columns:
            df[col] = df[col].astype(str).replace('nan', '').replace('<NA>', '')
        
        # Get selected cleaning options
        cleaning_options = request.form.getlist('cleaning_options')
        
        if not cleaning_options:
            flash('Please select at least one cleaning option', 'warning')
            preview_df = df.head(10)
            return render_template('index.html', 
                                 uploaded=True,
                                 preview_df=preview_df,
                                 original_shape=session['original_shape'],
                                 columns=list(df.columns),
                                 filename=session.get('filename', 'unknown'))
        
        # Apply cleaning
        df_cleaned = clean_dataframe(df, cleaning_options)
        
        # Save cleaned DataFrame
        session_id = str(uuid.uuid4())
        cleaned_filename = secure_filename(f"{session_id}_cleaned.csv")
        cleaned_filepath = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
        df_cleaned.to_csv(cleaned_filepath, index=False)
        
        session['cleaned_file'] = cleaned_filepath
        session['cleaned_shape'] = df_cleaned.shape
        session['cleaning_applied'] = cleaning_options
        
        # Show cleaned preview
        preview_df = df_cleaned.head(10)
        return render_template('index.html', 
                             uploaded=True,
                             cleaned=True,
                             preview_df=preview_df,
                             original_shape=session['original_shape'],
                             cleaned_shape=df_cleaned.shape,
                             columns=list(df_cleaned.columns),
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
