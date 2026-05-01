import subprocess
import os, sys
import argparse
import sqlite3
import gffutils
import json
from dtypes import blast, ipr, go, family, gene, kegg

def check_file_access(file_path):
    """
    Check if a file exists and is readable
    
    Args:
        file_path (str): Path to the file to check
        
    Returns:
        bool: True if file exists and is readable, False otherwise
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")
        
    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"Cannot read file at: {file_path}")
        
    return True


def compress_and_index_fasta(genome_path, fasta_prefix):
    """
    Compress fasta file with bgzip and create index with samtools if file ends with .fa or .fasta
    
    Args:
        genome_path (str): Path to the genome directory
        fasta_prefix (str): Prefix of the fasta file
        
    Returns:
        str: Path to the compressed fasta file
    """
    # Combine path and prefix to get full file path
    base_path = os.path.join(genome_path, fasta_prefix)
    
    # Check for different possible file extensions
    possible_files = [
        base_path + ext for ext in ['.fa', '.fasta', '.fa.gz', '.fasta.gz']
    ]
    
    # Find the first existing file
    file_path = None
    for f in possible_files:
        try:
            check_file_access(f)
            file_path = f
            break
        except (FileNotFoundError, PermissionError):
            continue
    
    if not file_path:
        raise FileNotFoundError(f"No valid fasta file found for prefix {fasta_prefix}")
    
    # Handle uncompressed fasta files
    if file_path.endswith(('.fa', '.fasta')):
        bgzip_output = file_path + '.gz'
        try:
            # Compress with bgzip
            subprocess.run(['bgzip', '-c', file_path], stdout=open(bgzip_output, 'wb'), check=True)
            file_path = bgzip_output
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error during compression: {str(e)}")
    
    # Check and create indices if needed
    gzi_index = file_path + '.gzi'
    fai_index = file_path + '.fai'
    
    if os.path.exists(gzi_index) and os.path.exists(fai_index):
        print(f"Indices already exist for {file_path}")
    else:
        try:
            # Create index with samtools
            subprocess.run(['samtools', 'faidx', file_path], check=True)
            print(f"Created indices for {file_path}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error during indexing: {str(e)}")
    
    return file_path

def delete_genome_db(conn):
    """
    Delete all tables that start with 'hse_' from the database
    
    Args:
        conn (sqlite3.Connection): Database connection handle
    """
    try:
        cursor = conn.cursor()
        
        # Get all tables that start with 'hse_'
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name LIKE 'hse_%'
        """)
        
        tables = cursor.fetchall()
        
        # Drop each table
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        conn.commit()
        print(f"Successfully deleted {len(tables)} HSE tables from database")
        
    except sqlite3.Error as e:
        raise Exception(f"Failed to delete HSE tables: {str(e)}")


def process_gff_file(genome_path, gff_name, db_path, operation):
    """
    Process GFF file based on operation (insert/delete) using SQLite database
    
    Args:
        genome_path (str): Path to genome folder
        gff_name (str): Name of the GFF file
        conn (sqlite3.Connection): Database connection handle
        operation (str): Operation to perform ('insert' or 'delete')
    """
    gff_path = os.path.join(genome_path, gff_name)
    check_file_access(gff_path)

    if operation == 'insert':
        # Check if GFF already exists
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='features'")
            exists = cursor.fetchone() is not None
        
        if not exists:
            gffutils.create_db(
                gff_path,
                dbfn=db_path,
                force=False,     # 不覆盖已有文件
                keep_order=True,
                merge_strategy='create_unique',
                sort_attribute_values=True
            )
        else:
            print(f"GFF data for {gff_name} already exists in database")
            
    elif operation == 'delete':
        # Delete all SQLite tables
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # Drop each table if it exists
            for table in tables:
                table_name = table[0]
                if table_name in ['meta', 'features', 'relations', 'duplicates', 'directives', 'autoincrements']:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            conn.commit()
        print(f"Successfully deleted GFF tables from database")
    else:
        raise ValueError("Invalid operation. Use 'insert' or 'delete'.")


def process_genome_annotations(genome_path):
    """
    Process genome annotation files and generate documentation
    
    Args:
        genome_path (str): Path to genome directory
        
    Returns:
        tuple: Contains gene_doc, transcript_doc, exon_doc, ipr_doc, go_doc, 
               kegg_doc and blast_all_doc
    """
    # Process family data
    family_file_path = os.path.join(genome_path, 'func_anno', 'itak/itak.txt')
    check_file_access(family_file_path)
    family_doc = family.generate_family_doc(family_file_path, 'iTAK')

    # process gff/gtf file using HSE method, to generate genes, transcripts, and exons docs
    gtf_file = os.path.join(genome_path, 'gene_model.gtf')
    canonical_transcripts_file = os.path.join(genome_path, 'canonical_transcripts.txt')
    ahrd_file = os.path.join(genome_path, 'func_anno', 'ahrd.csv')
    check_file_access(gtf_file)
    check_file_access(canonical_transcripts_file)
    check_file_access(ahrd_file)
    gene_doc, transcript_doc, exon_doc = gene.generate_transcript_doc(
        gtf_file, canonical_transcripts_file, ahrd_file, family_file_path
    )

    # process ipr, go, kegg, blast files and generate docs 
    ipr_file_path = os.path.join(genome_path, 'func_anno', 'protein.fa.rmpwy.xml.gz')
    check_file_access(ipr_file_path)
    ipr_doc = ipr.generate_ipr_doc(ipr_file_path)

    go_file_path = os.path.join(genome_path, 'func_anno', 'go_mrna.txt') 
    check_file_access(go_file_path)
    go_doc = go.generate_go_doc(go_file_path, 'go-basic.obo')

    kegg_file_path = os.path.join(genome_path, 'func_anno', 'kegg_mrna.txt') 
    check_file_access(kegg_file_path)
    kegg_doc = kegg.generate_kegg_doc(kegg_file_path)

    blast_files = {
        'TAIR': 'pep.dia.at.top5.xml.gz',
        'nr': 'pep.dia.nr.top5.xml.gz',
        'Swiss-Prot': 'pep.dia.sp.top5.xml.gz',
        'TrEMBL': 'pep.dia.tr.top5.xml.gz'
    }

    blast_all_doc = {}
    for db_name, blast_file in blast_files.items():
        blast_file_path = os.path.join(genome_path, 'func_anno', blast_file)
        check_file_access(blast_file_path)
        blast_doc = blast.generate_blast_doc(db_name, blast_file_path)
        blast_all_doc[db_name] = blast_doc

    return (gene_doc, transcript_doc, exon_doc, ipr_doc, go_doc, 
            kegg_doc, blast_all_doc, family_doc)

def read_key_value_file(filepath, meta_data):
    """
    Read key-value file with colon separator and merge with existing dict
    
    Args:
        filepath (str): Path to the key-value file
        meta_data (dict): Existing dictionary to merge with
        
    Returns:
        dict: Combined dictionary with file contents and existing data
    """
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    key, value = line.split(':', 1)
                    meta_data[key.strip()] = value.strip()
    
    # No return needed as we modified the dict reference directly


def parse_arguments():
    """
    Parse command line arguments for genome operations
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='Process genome operations')
    
    # Add required arguments
    parser.add_argument('--genome', '-g', 
                       type=str,
                       required=True,
                       help='Path to the genome folder')
    
    # Add operation argument with choices
    parser.add_argument('--operation', '-o',
                       type=str,
                       required=False,
                       default='insert',
                       choices=['insert', 'delete', 'compare'],
                       help='Operation to perform (insert, delete, or compare). Default: insert')
    
    # Parse arguments
    args = parser.parse_args()
    check_file_access(args.genome)
    return args


def main():
    """
    Main function to handle genome operations based on command line arguments
    """
    # Get command line arguments
    args = parse_arguments()
    genome_path = args.genome
    operation = args.operation

    db_path = os.path.join(genome_path, 'genome.db')

    # meta data for genome 
    # genome_id = os.path.join(genome_path, 'genome_id')

    # Read genome info files and convert to JSON
    meta_data = {}
    genome_info = os.path.join(genome_path, 'genome_info')
    genome_auto = os.path.join(genome_path, 'genome_auto') 
    
    try:
        check_file_access(genome_info)
        check_file_access(genome_auto)
        
        # Process files after validation
        read_key_value_file(genome_info, meta_data)
        read_key_value_file(genome_auto, meta_data)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error accessing genome info files: {str(e)}")
        sys.exit(1)

    # Process gff file and store it in to sqlite using gffutils 
    # process_gff_file(genome_path, 'gene_model.gff3', db_path, operation)

    # store the doc into sqlite database 
    try:
        # Get database connection
        conn = conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if operation == 'insert':
            # create index for fasta files
            # Required fasta files
            required_prefixes = ['genome', 'gene', 'protein', 'upstream', 'downstream']
            # Optional fasta files (at least one must exist)
            optional_pairs = [('mRNA', 'cds')]

            # Process required files
            for prefix in required_prefixes:
                compress_and_index_fasta(genome_path, prefix)

            # Process optional file pairs
            for file1, file2 in optional_pairs:
                file1_exists = False
                file2_exists = False
                
                try:
                    compress_and_index_fasta(genome_path, file1)
                    file1_exists = True
                except FileNotFoundError:
                    pass
                    
                try:
                    compress_and_index_fasta(genome_path, file2)
                    file2_exists = True
                except FileNotFoundError:
                    pass
                    
                if not (file1_exists or file2_exists):
                    raise FileNotFoundError(f"Neither {file1} nor {file2} fasta file found")

            # delete all tables in sqlite database
            delete_genome_db(conn)

            # Insert meta data into sqlite database
            meta_data_json = json.dumps(meta_data)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hse_meta (
                    genome_meta JSON NOT NULL
                )
            ''')  
            cursor.execute('INSERT INTO hse_meta (genome_meta) VALUES (?)', (meta_data_json,))

            # process genome annotation files and generate documentation
            gene_doc, transcript_doc, exon_doc, ipr_doc, go_doc, kegg_doc, blast_all_doc, family_doc = process_genome_annotations(genome_path)

            # Create hse_genes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hse_genes (
                    gene_id TEXT PRIMARY KEY,
                    chrom TEXT NOT NULL,
                    start INTEGER NOT NULL,
                    stop INTEGER NOT NULL,
                    strand TEXT NOT NULL,
                    description TEXT NOT NULL,
                    canonical_transcript TEXT NOT NULL,
                    family TEXT
                )
            ''')

            # Prepare SQL statement for batch insert
            insert_sql = '''
                INSERT INTO hse_genes (
                    gene_id, chrom, start, stop, strand, description, canonical_transcript, family
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''

            # Convert gene dictionary to list of tuples for batch insert
            gene_data = [
                (
                    gene['gene_id'],
                    gene['chrom'],
                    gene['start'],
                    gene['stop'],
                    gene['strand'],
                    gene['description'],
                    gene['canonical_transcript'],
                    gene.get('family', None)  # Family field can be null for some genes
                )
                for gene_id, gene in gene_doc.items()
            ]

            # Execute batch insert
            cursor.executemany(insert_sql, gene_data)
            
            # Create compound index for position-based queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_genes_position
                ON hse_genes(chrom, start, stop)
            ''')
            
            # Create index for gene_id lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_genes_gene_id
                ON hse_genes(gene_id)
            ''')
            
            # Create full-text search index for description searches
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_genes_description
                ON hse_genes(description)
            ''')

            # Create hse_exons table with auto-incrementing ID
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hse_exons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_type TEXT NOT NULL,
                    transcript_id TEXT NOT NULL,
                    gene_id TEXT NOT NULL,
                    chrom TEXT NOT NULL,
                    start INTEGER NOT NULL,
                    stop INTEGER NOT NULL,
                    strand TEXT NOT NULL
                )
            ''')

            # Prepare SQL statement for batch insert
            insert_sql = '''
                INSERT INTO hse_exons (
                    feature_type, transcript_id, gene_id, chrom, start, stop, strand
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            '''

            # Convert exon list to list of tuples for batch insert
            exon_data = [
                (
                    exon['feature_type'],
                    exon['transcript_id'],
                    exon['gene_id'],
                    exon['chrom'],
                    exon['start'],
                    exon['stop'],
                    exon['strand']
                )
                for exon in exon_doc
            ]

            # Execute batch insert
            cursor.executemany(insert_sql, exon_data)

            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_exons_transcript_id 
                ON hse_exons(transcript_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_exons_gene_id 
                ON hse_exons(gene_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_exons_position
                ON hse_exons(chrom, start, stop)
            ''')

            # Create hse_transcripts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hse_transcripts (
                    transcript_id TEXT PRIMARY KEY,
                    gene_id TEXT NOT NULL,
                    chrom TEXT NOT NULL,
                    start INTEGER NOT NULL,
                    stop INTEGER NOT NULL,
                    strand TEXT NOT NULL,
                    description TEXT NOT NULL,
                    blast_TAIR JSON,
                    blast_nr JSON,
                    blast_Swiss_Prot JSON,
                    blast_TrEMBL JSON,
                    InterPro JSON,
                    GO JSON,
                    KEGG JSON,
                    family JSON
                )
            ''')

            # Prepare SQL statement for batch insert
            insert_sql = '''
                INSERT INTO hse_transcripts (
                    transcript_id, gene_id, chrom, start, stop, strand, description, 
                    GO, KEGG, family, InterPro, blast_TAIR, blast_nr, blast_Swiss_Prot, blast_TrEMBL
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            # Convert transcript dictionary to list of tuples for batch insert
            transcript_data = [
                (
                    transcript_id,
                    transcript['gene_id'],
                    transcript['chrom'],
                    transcript['start'],
                    transcript['stop'],
                    transcript['strand'],
                    transcript['description'],
                    go_doc.get(transcript_id, None),  # Convert list to JSON string
                    kegg_doc.get(transcript_id, None),
                    family_doc.get(transcript_id, None),
                    ipr_doc.get(transcript_id, None),
                    blast_all_doc['TAIR'].get(transcript_id, None),
                    blast_all_doc['nr'].get(transcript_id, None),
                    blast_all_doc['Swiss-Prot'].get(transcript_id, None),
                    blast_all_doc['TrEMBL'].get(transcript_id, None)
                )
                for transcript_id, transcript in transcript_doc.items()
            ]

            # Execute batch insert
            cursor.executemany(insert_sql, transcript_data)

            # Create index on gene_id for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transcripts_gene_id 
                ON hse_transcripts(gene_id)
            ''')

            
        elif operation == 'delete':
            delete_genome_db(conn)
            print(f"Successfully deleted genome data for {genome_path}")
            
        elif operation == 'compare':
            pass
            # Compare genome data
            # cursor.execute("SELECT * FROM genome_info WHERE name = ?", 
            #             (os.path.basename(args.genome),))
            #print(f"Comparison results for {args.genome}")
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error processing genome operation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()