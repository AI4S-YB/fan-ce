import os
import sys
import subprocess
import pandas as pd
import numpy as np
import h5py
import gzip
import uuid
import csv
from typing import List, Tuple, Optional


def process_rnaseq_file(input_file, exp_h5_file=None):
    """
    Process matrix files (csv, txt etc) and store in HDF5 format
    Returns file name if file is successfully processed
    """
    # Check if input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} not found")

    # process input file is already in HDF5 format
    if input_file.endswith('.h5'):
        try:
            with h5py.File(input_file, 'r') as f:
                # Check required groups exist
                if 'count' not in f or 'fpkm' not in f or 'meta' not in f:
                    raise ValueError("Missing required groups (count, fpkm, meta)")
                
                # Check count group structure
                count_group = f['count']
                if 'matrix' not in count_group or 'samples' not in count_group:
                    raise ValueError("Count group missing required datasets (matrix, samples)")
                
                # Check fpkm group structure  
                fpkm_group = f['fpkm']
                if 'matrix' not in fpkm_group or 'samples' not in fpkm_group:
                    raise ValueError("FPKM group missing required datasets (matrix, samples)")
                
                # Check meta group structure
                meta_group = f['meta']
                if 'genes' not in meta_group:
                    raise ValueError("Meta group missing required dataset (genes)")
                
            return input_file
            
        except Exception as e:
            raise ValueError(f"Invalid HDF5 file structure: {str(e)}")
    
    # process input file if not in HDF5 format
    else:
        try:
            # Read the input file (auto-detect delimiter), handle both compressed and uncompressed files
            if input_file.endswith('.gz'):
                df = pd.read_csv(input_file, sep=None, engine='python', index_col=0, compression='gzip')
            else:
                df = pd.read_csv(input_file, sep=None, engine='python', index_col=0)
            
            # Validate matrix format
            if df.empty:
                raise ValueError("Empty file or invalid matrix format")
            
            # Create/open HDF5 file
            h5_file = exp_h5_file if exp_h5_file else input_file + '.h5'
            with h5py.File(h5_file, 'a') as f:

                # prepare gene names (index) in meta group
                gene_names = df.index.tolist()
                
                # Check if meta group exists, if not create it
                meta_group = f['meta'] if 'meta' in f else f.create_group('meta')
                
                # Check if genes dataset exists
                if 'genes' in meta_group:
                    # Read existing genes
                    existing_genes = [g.decode() for g in meta_group['genes'][:]]
                    # Compare with new genes
                    if existing_genes != gene_names:
                        raise ValueError("New genes do not match existing genes in HDF5 file")
                else:
                    # Convert gene names to fixed-length strings for HDF5 compatibility
                    max_length = max(len(str(name)) for name in gene_names)
                    gene_names_array = np.array(gene_names, dtype=f'S{max_length}')
                    gene_names_dataset = meta_group.create_dataset('genes',
                                                                data=gene_names_array)



                # Check if all values are integers
                is_count_data = np.all(df.values.astype(float).astype(int) == df.values.astype(float))
                
                # Determine group name based on data type，and create if not already created
                group_name = 'count' if is_count_data else 'fpkm'
                group = f[group_name] if group_name in f else f.create_group(group_name)

                # Store sample names (columns)
                sample_names = df.columns.tolist()
                
                # Check if samples dataset exists in the group
                if 'samples' in group:
                    # Read existing samples
                    existing_samples = [s.decode() for s in group['samples'][:]]
                    # Compare with new samples
                    if existing_samples != sample_names:
                        raise ValueError(f"New samples do not match existing samples in {group_name} group")
                    
                    # If samples match, check if matrix exists and matches
                    if 'matrix' in group:
                        #existing_matrix = group['matrix'][:]
                        #if not np.array_equal(existing_matrix, df.values):
                        #    raise ValueError(f"New matrix data does not match existing matrix in {group_name} group")
                        # if matrix exist, we think the data is the same, we don't need to overwrite it
                        print("The data is already exist, we don't need to overwrite it")
                        pass
                else:
                    # Create new samples dataset if it doesn't exist
                    max_sample_length = max(len(str(name)) for name in sample_names)
                    sample_names_array = np.array(sample_names, dtype=f'S{max_sample_length}')
                    sample_names_dataset = group.create_dataset('samples',
                                                            data=sample_names_array)

                    # the samples are new, the stroed matrix must be outdated, so delete it.
                    if 'matrix' in group:
                        del group['matrix']

                    # Store the expression matrix
                    dataset = group.create_dataset('matrix',
                                                data=df.values,
                                                dtype='int32' if is_count_data else 'float32')
                    # Create attributes for dimensions
                    dataset.attrs['n_genes'] = len(gene_names)
                    dataset.attrs['n_samples'] = len(sample_names)
                
                # Store the intpu file path to metadata
                # Store input file path in meta group based on data type
                file_path_key = f"{group_name}_file_path"
                if file_path_key in meta_group:
                    del meta_group[file_path_key]
                max_path_length = len(input_file)
                meta_group.create_dataset(file_path_key, data=np.array(input_file, dtype=f'S{max_path_length}'))

            return h5_file
        
        except Exception as e:
            raise ValueError(f"Error processing matrix file: {str(e)}")




def extract_expression_matrix(file_path: str, 
                              data_type: Optional[str] = 'fpkm',
                              genes: Optional[List[str]] = None,
                              samples: Optional[List[str]] = None,
                              temp_dir: str = "/tmp") -> Tuple[List[List[float]], List[str], List[str], Optional[str]]:
    with h5py.File(file_path, "r") as f:
        all_genes = [g.decode("utf-8") if isinstance(g, bytes) else g for g in f["/meta/genes"][:]]
        
        # Get samples based on expression type
        samples_path = f"/{data_type}/samples"
        all_samples = [s.decode("utf-8") if isinstance(s, bytes) else s for s in f[samples_path][:]]
        
        # Get expression matrix based on type
        matrix_path = f"/{data_type}/matrix"
        matrix = f[matrix_path]

        # 如果未提供，默认使用全部
        if not genes:
            gene_indices = list(range(len(all_genes)))
            gene_order_map = list(range(len(all_genes)))
            sorted_gene_indices = gene_indices
        else:
            # 获取用户指定基因的索引
            gene_indices = [all_genes.index(g) for g in genes]
            # 创建排序映射：原顺序位置 -> 排序后位置
            gene_order_map = sorted(range(len(gene_indices)), key=lambda i: gene_indices[i])
            # 按HDF5要求排序索引
            sorted_gene_indices = [gene_indices[i] for i in gene_order_map]
        
        # Return all samples if samples parameter is None or empty list
        if not samples:
            sample_indices = list(range(len(all_samples)))
            sample_order_map = list(range(len(all_samples)))
            sorted_sample_indices = sample_indices
        else:
            # 获取用户指定样本的索引
            sample_indices = [all_samples.index(s) for s in samples]
            # 创建排序映射：原顺序位置 -> 排序后位置
            sample_order_map = sorted(range(len(sample_indices)), key=lambda i: sample_indices[i])
            # 按HDF5要求排序索引
            sorted_sample_indices = [sample_indices[i] for i in sample_order_map]

        # 使用排序后的索引提取数据（满足HDF5递增索引要求）
        temp_matrix = matrix[sorted_gene_indices, :][:, sorted_sample_indices]
        
        # 重新排列数据以匹配用户指定的顺序
        # 创建逆向映射：排序后位置 -> 原顺序位置
        gene_reorder_map = [0] * len(gene_order_map)
        for i, sorted_pos in enumerate(gene_order_map):
            gene_reorder_map[sorted_pos] = i
            
        sample_reorder_map = [0] * len(sample_order_map)
        for i, sorted_pos in enumerate(sample_order_map):
            sample_reorder_map[sorted_pos] = i
        
        # 按用户指定的顺序重新排列矩阵
        submatrix = temp_matrix[gene_reorder_map, :][:, sample_reorder_map]
        
        # 按用户指定的顺序获取基因和样本名称
        sub_genes = [all_genes[i] for i in gene_indices] if genes else [all_genes[i] for i in gene_indices]
        sub_samples = [all_samples[i] for i in sample_indices] if samples else [all_samples[i] for i in sample_indices]

    est_size = submatrix.size * 4
    if est_size > 1_000_000:
        out_csv = os.path.join(temp_dir, f"expression_{uuid.uuid4().hex}.csv.gz")
        with gzip.open(out_csv, "wt") as out_f:
            writer = csv.writer(out_f)
            writer.writerow(["gene"] + sub_samples)
            for i, row in enumerate(submatrix):
                writer.writerow([sub_genes[i]] + list(row))
        return [], sub_genes, sub_samples, out_csv
    else:
        return submatrix.tolist(), sub_genes, sub_samples, None


def load_gene_sample_names(file_path: str, max_records: Optional[int] = 1000) -> Tuple[List[str], List[str]]:
    with h5py.File(file_path, "r") as f:
        # Return genes and samples up to max_records limit
        all_genes = [g.decode() if isinstance(g, bytes) else g for g in f["/meta/genes"][:max_records]]
        all_samples = [s.decode() if isinstance(s, bytes) else s for s in f["/count/samples"][:max_records]]
    return all_genes, all_samples
