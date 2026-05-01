import pandas as pd


def extract_expression(txt_file, gene_ids, sample_ids):
    try:
        expression_matrix = pd.read_csv(txt_file, sep="\t", index_col=0)
        missing_genes = [gene for gene in gene_ids if gene not in expression_matrix.index]
        if missing_genes:
            raise ValueError(f"The following gene IDs were not found in the expression matrix: {missing_genes}")
        missing_samples = [sample for sample in sample_ids if sample not in expression_matrix.columns]
        if missing_samples:
            raise ValueError(f"The following sample IDs were not found in the expression matrix: {missing_samples}")
        extracted_data = expression_matrix.loc[gene_ids, sample_ids]
        return extracted_data
    except FileNotFoundError:
        raise FileNotFoundError(f"Expression file '{txt_file}' not found.")
    except pd.errors.EmptyDataError:
        raise ValueError(f"The expression file '{txt_file}' is empty or improperly formatted.")
