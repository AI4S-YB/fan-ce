import os
import subprocess
import sys


def process_tabix_file(input_file, file_type):
    """
    Process files that can be indexed by tabix
    Returns the filename of the processed and indexed file
    """
    
    # Check if input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} not found")
    
    # Check if file is already compressed and indexed
    if input_file.endswith('.gz'):
        # Check if both .gz file and .tbi index exist
        if os.path.exists(input_file) and os.path.exists(input_file + '.tbi'):
            return input_file
        else:
            raise ValueError("Found .gz file but cannot verify if it was compressed with bgzip. Please ensure the file is properly compressed with bgzip before indexing.")

    # Check if there's a leftover .gz file from previous processing
    if os.path.exists(input_file + '.gz') and os.path.exists(input_file + '.gz.tbi'):
        return input_file + '.gz'

        
    # Validate file format by checking first few lines
    try:
        with open(input_file) as f:
            # Skip comment lines starting with #
            line = f.readline()
            while line:
                if not line.startswith('#'):
                    break
                line = f.readline()
            
            # Handle case where file only contains comments or is empty
            if not line:
                raise ValueError("File contains no data lines after comments")
            
            # Check if first non-comment line has chr, start, end columns
            fields = line.strip().split('\t')
            if len(fields) < 3:
                raise ValueError("File must have at least 3 columns (chr, start, end)")
            
            # Try to validate that second and third columns are integers
            try:
                int(fields[1])
                int(fields[2])
            except ValueError:
                raise ValueError("Second and third columns must be integers representing start and end positions")
    
    except Exception as e:
        raise ValueError(f"Invalid file format: {str(e)}")
    
    try:
        # Compress file with bgzip if not already compressed
        if not input_file.endswith('.gz'):
            compressed_file = input_file + '.gz'
            subprocess.run(['bgzip', '-c', input_file], stdout=open(compressed_file, 'wb'), check=True)
        
            # input_file = compressed_file
        
        # Create tabix index if it doesn't exist
        if not os.path.exists(compressed_file + '.tbi'):
            # Use generic indexing with sequence name in column 1, start in 2, end in 3
            subprocess.run(['tabix', '-s', '1', '-b', '2', '-e', '3', compressed_file], check=True)
                
        return compressed_file
        
    except subprocess.CalledProcessError as e:
        print(f"Error processing file: {str(e)}")
        return None


