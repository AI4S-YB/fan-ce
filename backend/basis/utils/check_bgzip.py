import gzip
import os
import sys

def check_compression_type(file_path):
    """
    Check if a .gz file is compressed using GZIP or BGZIP
    
    Args:
        file_path (str): Path to the .gz file
        
    Returns:
        str: Compression type ("GZIP", "BGZIP", "Not GZIP or BGZIP", or "Unknown compression format")
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return "File not found"
        
    # Check if file has .gz extension
    if not file_path.endswith('.gz'):
        return "Not a .gz file"
    
    try:
        with open(file_path, 'rb') as f:
            # Check first few bytes for gzip magic number
            #if f.read(2) != b'\x1f\x8b':
            #    return "Not GZIP or BGZIP"
            
            # Return to start and try reading as gzip
            f.seek(0)
            with gzip.GzipFile(fileobj=f) as gz:
                # Read first byte to verify it's readable
                gz.read(1)
                
                # Check for BGZIP by looking for EOF marker
                f.seek(-28, 2)  # Go to expected position of BGZIP EOF marker
                if f.read(4) == b'BC\x02\x00':
                    return "BGZIP"
                return "GZIP"
                
    except Exception as e:
        return "Unknown compression format"

if __name__ == "__main__":
    
    if len(sys.argv) != 2:
        print("Usage: python check_bgzip.py <gz_file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    result = check_compression_type(file_path)
    print(f"The file is compressed using: {result}")
