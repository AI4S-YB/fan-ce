import os
import sqlite3
from typing import List, Dict, Any

def query_sqlite(db_path: str, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Query SQLite database and return results as a list of dictionaries.
    :param db_path: Path to the SQLite database file.
    :param query: SQL query string.
    :param params: Tuple of parameters for the query.
    :return: List of dictionaries representing the query results.
    """
    # Check if file exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    # Check if file is readable
    if not os.access(db_path, os.R_OK):
        raise PermissionError(f"Database file is not readable: {db_path}")
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to connect to database: {str(e)}")




