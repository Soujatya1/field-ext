import streamlit as st
import os
import io
from google.cloud import vision
from google.oauth2 import service_account
import re
import json
import pandas as pd

# Set page config
st.set_page_config(
    page_title="Salary Document Processor",
    page_icon="💼",
    layout="wide"
)

# Application title and description
st.title("Salary Document Processor")
st.write("Upload your salary slips and ITR documents to extract information and perform calculations.")

# Function to process the document with Google Vision API
def process_document(file_bytes, api_key):
    """Process document using Google Vision API and extract text"""
    # Create a client
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(api_key)
    )
    client = vision.ImageAnnotatorClient(credentials=credentials)
    
    # Read image content
    content = file_bytes
    
    # Create image object
    image = vision.Image(content=content)
    
    # Perform text detection
    response = client.text_detection(image=image)
    text = response.text_annotations[0].description if response.text_annotations else ""
    
    if response.error.message:
        st.error(f"Error from Google Vision API: {response.error.message}")
        return None
    
    return text

# Function to extract fields from salary slip
def extract_salary_fields(text):
    """Extract relevant fields from salary slip text"""
    results = {}
    
    # Common patterns to look for in salary slips
    patterns = {
        'employee_name': r'(?:Name|Employee Name|Employee)\s*:?\s*([A-Za-z\s]+)',
        'employee_id': r'(?:Employee ID|Emp ID|Employee No|ID)\s*:?\s*([A-Za-z0-9]+)',
        'basic_salary': r'(?:Basic Salary|Basic Pay|Basic)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'hra': r'(?:HRA|House Rent Allowance)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'pf': r'(?:PF|Provident Fund)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'gross_salary': r'(?:Gross Salary|Gross Pay|Gross)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'net_amount': r'(?:Net Amount|Net Salary|Net Pay|Take Home|Total|Net)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'tax_deducted': r'(?:Tax Deducted|TDS|Income Tax)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
    }
    
    # Extract fields using regex patterns
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if field in ['basic_salary', 'hra', 'pf', 'gross_salary', 'net_amount', 'tax_deducted']:
                # Convert to float and handle commas in numbers
                value = match.group(1).replace(',', '')
                try:
                    results[field] = float(value)
                except ValueError:
                    results[field] = match.group(1)
            else:
                results[field] = match.group(1).strip()
    
    return results

# Function to extract fields from ITR document
def extract_itr_fields(text):
    """Extract relevant fields from ITR document text"""
    results = {}
    
    # Common patterns to look for in ITR documents
    patterns = {
        'pan': r'(?:PAN|Permanent Account Number)\s*:?\s*([A-Z0-9]+)',
        'assessment_year': r'(?:Assessment Year|AY)\s*:?\s*(20\d{2}-\d{2}|20\d{2})',
        'total_income': r'(?:Total Income|Gross Total Income)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'taxable_income': r'(?:Taxable Income|Net Taxable Income)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'tax_payable': r'(?:Tax Payable|Total Tax Payable)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
        'tax_paid': r'(?:Tax Paid|Total Tax Paid)\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)',
    }
    
    # Extract fields using regex patterns
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if field in ['total_income', 'taxable_income', 'tax_payable', 'tax_paid']:
                # Convert to float and handle commas in numbers
                value = match.group(1).replace(',', '')
                try:
                    results[field] = float(value)
                except ValueError:
                    results[field] = match.group(1)
            else:
                results[field] = match.group(1).strip()
    
    return results

# Function to perform calculations based on extracted fields
def perform_calculations(salary_data, itr_data):
    """Perform calculations based on extracted data"""
    calculations = {}
    
    # Calculate annual salary from monthly net amount
    if 'net_amount' in salary_data:
        calculations['annual_salary'] = salary_data['net_amount'] * 12
    
    # Calculate monthly salary from annual income in ITR
    if 'total_income' in itr_data:
        calculations['monthly_income_from_itr'] = itr_data['total_income'] / 12
    
    # Calculate tax percentage
    if 'gross_salary' in salary_data and 'tax_deducted' in salary_data and salary_data['gross_salary'] > 0:
        calculations['tax_percentage'] = (salary_data['tax_deducted'] / salary_data['gross_salary']) * 100
    
    # Calculate annual tax from monthly tax deducted
    if 'tax_deducted' in salary_data:
        calculations['annual_tax'] = salary_data['tax_deducted'] * 12
    
    # Calculate difference between ITR total income and calculated annual salary
    if 'total_income' in itr_data and 'annual_salary' in calculations:
        calculations['income_difference'] = itr_data['total_income'] - calculations['annual_salary']
    
    return calculations

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Document Processing", "Salary Analysis", "Settings"])

# Settings tab
with tab3:
    st.header("API Settings")
    
    # Google Cloud Vision API Key
    api_key = st.text_area(
        "Enter your Google Cloud Vision API Key (JSON format)",
        height=150,
        help="Paste your Google Cloud Vision API credentials in JSON format"
    )
    
    if api_key:
        # Save API key to session state
        st.session_state['api_key'] = api_key
        st.success("API key saved!")
    
    # Display instructions
    st.subheader("Instructions")
    st.write("""
    1. Enter your Google Cloud Vision API key in JSON format
    2. Upload salary slip and/or ITR documents in the 'Document Processing' tab
    3. View extracted information and calculations in the 'Salary Analysis' tab
    4. The application will automatically extract relevant fields and perform calculations
    """)

# Document Processing tab
with tab1:
    st.header("Upload Documents")
    
    # File uploader for salary slip
    salary_slip = st.file_uploader("Upload Salary Slip", type=["jpg", "jpeg", "png", "pdf"], key="salary_slip")
    
    # File uploader for ITR document
    itr_document = st.file_uploader("Upload ITR Document", type=["jpg", "jpeg", "png", "pdf"], key="itr_document")
    
    # Process button
    if st.button("Process Documents"):
        if 'api_key' not in st.session_state or not st.session_state['api_key']:
            st.error("Please enter your Google Cloud Vision API key in the Settings tab first.")
        else:
            # Process salary slip
            salary_data = {}
            if salary_slip is not None:
                with st.spinner("Processing salary slip..."):
                    # Read file bytes
                    file_bytes = salary_slip.getvalue()
                    
                    # Process with Google Vision API
                    extracted_text = process_document(file_bytes, st.session_state['api_key'])
                    
                    if extracted_text:
                        # Extract fields from text
                        salary_data = extract_salary_fields(extracted_text)
                        
                        # Save to session state
                        st.session_state['salary_data'] = salary_data
                        st.session_state['salary_text'] = extracted_text
                        
                        st.success("Salary slip processed successfully!")
                    else:
                        st.error("Failed to process salary slip.")
            
            # Process ITR document
            itr_data = {}
            if itr_document is not None:
                with st.spinner("Processing ITR document..."):
                    # Read file bytes
                    file_bytes = itr_document.getvalue()
                    
                    # Process with Google Vision API
                    extracted_text = process_document(file_bytes, st.session_state['api_key'])
                    
                    if extracted_text:
                        # Extract fields from text
                        itr_data = extract_itr_fields(extracted_text)
                        
                        # Save to session state
                        st.session_state['itr_data'] = itr_data
                        st.session_state['itr_text'] = extracted_text
                        
                        st.success("ITR document processed successfully!")
                    else:
                        st.error("Failed to process ITR document.")
            
            # Perform calculations
            if salary_data or itr_data:
                calculations = perform_calculations(salary_data, itr_data)
                st.session_state['calculations'] = calculations

# Salary Analysis tab
with tab2:
    st.header("Analysis Results")
    
    # Create columns for displaying results
    col1, col2 = st.columns(2)
    
    # Display salary slip information
    with col1:
        st.subheader("Salary Slip Information")
        if 'salary_data' in st.session_state and st.session_state['salary_data']:
            data = st.session_state['salary_data']
            
            # Display data in a table
            salary_df = pd.DataFrame([(k, v) for k, v in data.items()], columns=['Field', 'Value'])
            st.table(salary_df)
            
            # Option to view raw text
            if st.checkbox("Show raw text from salary slip"):
                st.text_area("Extracted Text", st.session_state['salary_text'], height=200)
        else:
            st.info("No salary slip data available. Please upload and process a salary slip.")
    
    # Display ITR information
    with col2:
        st.subheader("ITR Document Information")
        if 'itr_data' in st.session_state and st.session_state['itr_data']:
            data = st.session_state['itr_data']
            
            # Display data in a table
            itr_df = pd.DataFrame([(k, v) for k, v in data.items()], columns=['Field', 'Value'])
            st.table(itr_df)
            
            # Option to view raw text
            if st.checkbox("Show raw text from ITR document"):
                st.text_area("Extracted Text", st.session_state['itr_text'], height=200)
        else:
            st.info("No ITR data available. Please upload and process an ITR document.")
    
    # Display calculations
    st.subheader("Calculations")
    if 'calculations' in st.session_state and st.session_state['calculations']:
        data = st.session_state['calculations']
        
        # Create a formatted display of calculations
        calc_df = pd.DataFrame([(k, v) for k, v in data.items()], columns=['Calculation', 'Value'])
        
        # Format the calculation names to be more readable
        calc_df['Calculation'] = calc_df['Calculation'].apply(lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        
        # Format currency values
        for i, row in calc_df.iterrows():
            if isinstance(row['Value'], (int, float)):
                calc_df.at[i, 'Value'] = f"₹ {row['Value']:,.2f}"
        
        st.table(calc_df)
        
        # Add visualization if we have enough data
        if 'annual_salary' in data:
            st.subheader("Income Visualization")
            
            # Create bar chart for income breakdown
            chart_data = {}
            
            if 'annual_salary' in data:
                chart_data['Annual Salary (from slip)'] = data['annual_salary']
            
            if 'total_income' in st.session_state.get('itr_data', {}):
                chart_data['Total Income (from ITR)'] = st.session_state['itr_data']['total_income']
            
            if 'annual_tax' in data:
                chart_data['Annual Tax'] = data['annual_tax']
            
            if chart_data:
                chart_df = pd.DataFrame(list(chart_data.items()), columns=['Category', 'Amount'])
                st.bar_chart(chart_df.set_index('Category'))
    else:
        st.info("No calculations available. Please process documents to generate calculations.")

# Footer
st.markdown("---")
st.caption("This application extracts information from salary slips and ITR documents using Google Vision API. The extracted information is used to perform various calculations related to salary and taxes.")
