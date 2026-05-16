import os
import sys
import pandas as pd
import sqlite3
import uuid
from typing import List, Tuple, Optional, Dict, Any

def get_sqlite_path(xls_path: str) -> str:
    """
    Convert Excel file path to SQLite file path
    Args:
        xls_path: Path to Excel file
    Returns:
        SQLite database file path
    Raises:
        ValueError: If file path is not absolute or file not accessible
        FileNotFoundError: If file does not exist
    """
    # Check if path is absolute
    if not os.path.isabs(xls_path):
        raise ValueError(f"File path must be absolute: {xls_path}")

    # Check if file exists
    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"Excel file not found: {xls_path}")

    # Check if file is accessible
    if not os.access(xls_path, os.R_OK):
        raise ValueError(f"Excel file is not readable: {xls_path}")

    # Check if file has valid Excel extension
    if not xls_path.endswith(('.xlsx', '.xls')):
        raise ValueError(f"File must be an Excel file (.xlsx or .xls): {xls_path}")

    # Get base path without extension
    base_path = os.path.splitext(xls_path)[0]
    
    # Return path with .db extension
    return f"{base_path}.db"



def process_phenome_file(input_file: str, sqlite_file: str) -> str:
    """
    Process phenome Excel files and store in SQLite database
    Returns SQLite file path if file is successfully processed
    """
    
    # Get SQLite file path using get_sqlite_path function
    sqlite_file = get_sqlite_path(input_file)
    
    try:
        # Read first sheet from Excel file
        df = pd.read_excel(input_file, sheet_name=0)
        
        # Verify columns exist
        if len(df.columns) < 4:
            raise ValueError("Excel file must have at least 4 columns")
            
        # Only rename first column and keep other columns except Chinese_Name and English_Name
        first_col_name = df.columns[0]
        other_cols = df.columns[3:]
        
        df = df[[first_col_name] + list(other_cols)]
        df = df.rename(columns={first_col_name: 'ID'})
        
        # Connect to SQLite database
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        
        # Create table and insert data
        df.to_sql('phenotype', conn, if_exists='replace', index=False)
        
        print(f"Processed phenotype data with {len(df)} rows and {len(df.columns)} columns")
         
    except Exception as e:
        raise ValueError(f"Error processing phenome file: {str(e)}")


def get_phenome_data(sqlite_file: str,
                    traits: Optional[List[str]] = None,
                    samples: Optional[List[str]] = None,
                    limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Extract phenome data from SQLite database with traits as rows and sample values as columns
    """
    if not os.path.exists(sqlite_file):
        raise FileNotFoundError(f"SQLite file {sqlite_file} not found")
    
    try:
        conn = sqlite3.connect(sqlite_file)
        
        # Build base query
        query = "SELECT * FROM phenotype"
        conditions = []
        
        # Only apply sample filtering if samples list is provided and not empty
        if samples and len(samples) > 0:
            sample_list = "','".join(samples)
            conditions.append(f"ID IN ('{sample_list}')")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        if limit:
            query += f" LIMIT {limit}"
        
        # Execute query
        df = pd.read_sql_query(query, conn)
        
        # Only filter traits if traits list is provided and not empty
        if traits and len(traits) > 0:
            available_cols = df.columns.tolist()
            selected_cols = [col for col in traits if col in available_cols]
            if 'ID' in available_cols:
                selected_cols.insert(0, 'ID')
            df = df[selected_cols]
        
        conn.close()
        
        # Transpose dataframe to have traits as rows
        df_transposed = df.set_index('ID').transpose()
        
        # Convert to list of dictionaries where each dict represents a trait
        data = []
        for trait in df_transposed.index:
            trait_data = {'trait': trait}
            trait_data.update(df_transposed.loc[trait].to_dict())
            data.append(trait_data)
            
        # Columns will be 'trait' followed by sample IDs
        columns = ['trait'] + list(df_transposed.columns)
        
        return data, columns
        
    except Exception as e:
        raise ValueError(f"Error querying phenome data: {str(e)}")


def get_table_columns(sqlite_file: str) -> List[str]:
    """
    Get column names for phenotype table
    """
    if not os.path.exists(sqlite_file):
        raise FileNotFoundError(f"SQLite file {sqlite_file} not found")
    
    try:
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(phenotype)")
        # Skip the first column (ID) and return remaining columns
        columns = [row[1] for row in cursor.fetchall()[1:]]
        
        conn.close()
        return columns
        
    except Exception as e:
        raise ValueError(f"Error getting table columns: {str(e)}")

def get_first_column_data(sqlite_file: str) -> List[str]:
    """
    Get first column data from phenotype table
    Args:
        sqlite_file: Path to SQLite database file
    Returns:
        List of values from first column
    Raises:
        FileNotFoundError: If SQLite file not found
        ValueError: If error occurs while querying data
    """
    if not os.path.exists(sqlite_file):
        raise FileNotFoundError(f"SQLite file {sqlite_file} not found")
    
    try:
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        
        # Get first column name
        cursor.execute("PRAGMA table_info(phenotype)")
        first_col = cursor.fetchone()[1]
        
        # Get data from first column
        cursor.execute(f"SELECT {first_col} FROM phenotype")
        data = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return data
        
    except Exception as e:
        raise ValueError(f"Error getting first column data: {str(e)}")
