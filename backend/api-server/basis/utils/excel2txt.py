import pandas as pd
import os
import sys

def excel_to_text(excel_file, output_dir=None):
    """
    Extract tables from Excel file and save them as text files
    
    Args:
        excel_file (str): Path to the Excel file
        output_dir (str): Directory to save output text files. If None, use same directory as Excel file
    """
    try:
        # Read all sheets from Excel file
        excel = pd.ExcelFile(excel_file)
        sheet_names = excel.sheet_names
        
        # Create output directory if not exists
        if output_dir is None:
            output_dir = os.path.splitext(excel_file)[0]
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each sheet
        for sheet in sheet_names:
            # Read sheet into DataFrame
            df = pd.read_excel(excel_file, sheet_name=sheet)
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(excel_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}_{sheet}.txt")
            
            # Save DataFrame to text file
            df.to_csv(output_file, sep='\t', index=False)
            
        return True
        
    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        return False

if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("Usage: python excel2txt.py <excel_file>")
        sys.exit(1)
        
    excel_file = sys.argv[1]
    value = excel_to_text(excel_file)
    print(value)
