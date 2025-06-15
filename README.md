# ContactCleaner - Apollo.io CSV Processor

A Flask web application for cleaning and processing Apollo.io contact CSV files with an intuitive web interface.

## Features

- **File Upload**: Upload Apollo.io CSV files through a clean web interface
- **Data Preview**: Preview the first 10 rows of your data before cleaning
- **Multiple Cleaning Options**:
  - Trim whitespace from all text fields
  - Remove rows with missing First Name or Last Name
  - Standardize titles to proper case
  - Remove duplicate rows based on email or phone number
  - Normalize phone numbers to E.164 format
  - Convert email addresses to lowercase
  - Filter to keep only essential columns
- **Live Statistics**: See row and column counts before and after cleaning
- **Download**: Download the cleaned data as a CSV file
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Backend**: Flask, Pandas, phonenumbers
- **Frontend**: Bootstrap 5, HTML5, CSS3
- **Data Processing**: Pandas for data manipulation
- **Phone Validation**: phonenumbers library for E.164 formatting

## Installation & Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Step 1: Clone or Download

Download the project files to your local machine.

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage Instructions

### 1. Upload Your CSV File

1. Open your web browser and go to `http://localhost:5000`
2. Click on the file upload area or drag and drop your Apollo.io CSV file
3. Click "Upload & Preview" to process the file

### 2. Preview Your Data

- View the first 10 rows of your data
- Check file statistics (rows and columns)
- Review all available columns

### 3. Select Cleaning Options

Choose from the available data cleaning options:

- **Trim Whitespace**: Removes extra spaces from all text fields
- **Remove Missing Names**: Drops rows where First Name or Last Name is empty
- **Standardize Titles**: Converts job titles to proper case (e.g., "secretary" → "Secretary")
- **Remove Email Duplicates**: Keeps only the first occurrence of each email address
- **Remove Phone Duplicates**: Keeps only the first occurrence of each phone number
- **Normalize Phone Numbers**: Converts phone numbers to international E.164 format
- **Lowercase Emails**: Converts all email addresses to lowercase
- **Keep Essential Columns Only**: Filters data to include only:
  - First Name
  - Last Name
  - Title
  - Company
  - Email
  - Phone Number (unified from various phone columns)
  - Location (combined from City, State, Country)

### 4. Clean Your Data

1. Select the cleaning options you want to apply
2. Click "Clean Data" to process your file
3. Review the cleaned data preview

### 5. Download Results

1. Click "Download Clean CSV" to save the processed file
2. The file will be downloaded as `cleaned_contacts.csv`

## File Structure

```
ContactCleaner/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main HTML template
├── uploads/              # Temporary file storage (auto-created)
└── README.md            # This file
```

## Configuration

### Environment Variables (Optional)

You can customize the application by setting these environment variables:

- `FLASK_ENV`: Set to `development` for debug mode
- `SECRET_KEY`: Custom secret key for sessions (recommended for production)

### Application Settings

In `app.py`, you can modify:

- `MAX_CONTENT_LENGTH`: Maximum file upload size (default: 16MB)
- `UPLOAD_FOLDER`: Temporary file storage location
- `ALLOWED_COLUMNS`: List of columns to keep when filtering

## Data Processing Details

### Phone Number Processing

The application intelligently handles phone numbers by:

1. **Detecting Phone Columns**: Automatically finds columns containing phone-related data
2. **Unifying Data**: Creates a single "Phone Number" column from multiple phone fields
3. **Normalization**: Uses the `phonenumbers` library to convert to E.164 format
4. **Error Handling**: Invalid numbers are left unchanged rather than causing errors

### Location Processing

Creates a unified "Location" column by combining:
- City
- State
- Country

### Duplicate Removal

- **Email Duplicates**: Based on exact email address matches
- **Phone Duplicates**: Based on phone number matches (after normalization if selected)
- **Strategy**: Keeps the first occurrence and removes subsequent duplicates

## Troubleshooting

### Common Issues

1. **File Upload Fails**
   - Ensure the file is a valid CSV format
   - Check that file size is under 16MB
   - Verify the CSV has proper headers

2. **Phone Number Normalization Issues**
   - Invalid phone numbers are left unchanged
   - The app assumes US format for numbers without country codes
   - International numbers should include country codes

3. **Memory Issues with Large Files**
   - The application loads the entire CSV into memory
   - For very large files (>100MB), consider splitting the file first

### Error Messages

- **"No file selected"**: Choose a CSV file before uploading
- **"Please upload a CSV file"**: Only .csv files are accepted
- **"The uploaded CSV file is empty"**: File contains no data
- **"Error reading CSV file"**: File format issue or corrupted data

## Security Notes

- Files are temporarily stored on the server and cleaned up automatically
- Session data is used to track user files
- For production use, change the `SECRET_KEY` in `app.py`
- The application runs in debug mode by default - disable for production

## Development

### Adding New Cleaning Options

1. Add the new option to the HTML form in `templates/index.html`
2. Implement the cleaning logic in the `clean_dataframe()` function in `app.py`
3. Add the option description to the README

### Customizing the UI

- Modify `templates/index.html` for layout changes
- CSS styles are embedded in the HTML template
- Bootstrap 5 classes are used for responsive design

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review error messages in the web interface
3. Check the console output where you ran `python app.py`

---

**ContactCleaner** - Making your Apollo.io contact data clean and organized! 🧹✨ 