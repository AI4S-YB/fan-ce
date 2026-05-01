import os
import tempfile
import subprocess
import gzip
import shutil

from basis.core.path_utils import get_genome_db_path
from basis.core.sqlite_utils import query_sqlite


def process_variant_file(input_file):
    """
    Process variant files (VCF/BCF) and create indexes
    Returns True if file is valid and properly indexed
    """

    # Check if input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} not found")

    # Process VCF file
    if input_file.endswith('.vcf'):
        # Convert to BCF and index
        bcf_file = input_file.replace('.vcf', '.bcf')
        subprocess.run(['bcftools', 'view', '-Ob', '-o', bcf_file, input_file], check=True)
        subprocess.run(['bcftools', 'index', bcf_file], check=True)
        input_file = bcf_file

    # Process BCF file
    elif input_file.endswith('.bcf'):
        # Check if index exists, create if not
        if not os.path.exists(input_file + '.csi'):
            subprocess.run(['bcftools', 'index', input_file], check=True)

    # Process compressed VCF file
    elif input_file.endswith('.vcf.gz'):
        # Check if index exists, create if not
        if not os.path.exists(input_file + '.tbi') and not os.path.exists(input_file + '.csi'):
            subprocess.run(['bcftools', 'index', input_file], check=True)

    else:
        raise ValueError("Input file must be .vcf, .bcf, or .vcf.gz format")

    # Validate file format by querying
    try:
        result = subprocess.run(
            ['bcftools', 'query', '-f', '%CHROM\t%POS\t%REF\t%ALT\n', input_file],
            capture_output=True,
            text=True,
            check=True
        )
        # Check if output contains valid format
        lines = result.stdout.strip().split('\n')
        if lines and len(lines[0].split('\t')) == 4:
            return input_file
            
        return False
    except subprocess.CalledProcessError:
        return False


def check_vcf_file(vcf_path: str) -> bool:
    """
    Check if VCF file exists, is readable, has correct extension and index file
    
    Args:
        vcf_path: Path to the VCF file
        
    Returns:
        bool: True if file is valid, False otherwise
    """
    # Check if file exists
    if not os.path.exists(vcf_path):
        raise FileNotFoundError(f"VCF file not found: {vcf_path}")
    
    # Check if file is readable
    if not os.access(vcf_path, os.R_OK):
        raise PermissionError(f"VCF file is not readable: {vcf_path}")
    
    # Check file extension
    if not (vcf_path.endswith('.bcf') or vcf_path.endswith('.vcf.gz')):
        raise ValueError(f"Invalid file format. File must be .bcf or .vcf.gz: {vcf_path}")
    
    # Check for index file.
    # bgzip VCFs may legitimately use either tabix (.tbi) or CSI (.csi).
    if vcf_path.endswith('.vcf.gz'):
        index_candidates = [vcf_path + '.tbi', vcf_path + '.csi']
    else:
        index_candidates = [vcf_path + '.csi']
    if not any(os.path.exists(index_path) for index_path in index_candidates):
        raise FileNotFoundError(f"Index file not found: {index_candidates[0]}")

    return True


def get_gene_region(genome_id: str, gene_id: str):
    db_path = get_genome_db_path(genome_id)
    result = query_sqlite(db_path, "SELECT chrom, start, stop FROM hse_genes WHERE gene_id=?", (gene_id,))
    if not result:
        raise ValueError(f"gene_id {gene_id} not found")
    return result[0]["chrom"], result[0]["start"], result[0]["stop"]


def extract_variants(vcf_path, regions, include_samples=None, exclude_samples=None):
    tmp_dir = tempfile.mkdtemp()
    raw_out = os.path.join(tmp_dir, "output.vcf")

    cmd = ["bcftools", "view", vcf_path]

    if regions:
        cmd += ["-r", ",".join(regions)]

    if include_samples:
        cmd += ["-s", ",".join(include_samples)]
    elif exclude_samples:
        cmd += ["--samples-exclude", ",".join(exclude_samples)]

    cmd += ["-Ov", "-o", raw_out]

    print(cmd)

    subprocess.run(cmd, check=True)

    gz_path = raw_out + ".gz"
    with open(raw_out, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    size = os.path.getsize(gz_path)
    preview = None
    if size <= 1024 * 1024:
        with gzip.open(gz_path, "rt") as f:
            lines = f.readlines()
            if lines:  # Check if file is not empty
                preview = "".join(lines[:100])  # up to 100 lines including the last line
                

    return {
        "vcf_path": gz_path,
        "size": size,
        "preview": preview,
    }




def generate_variant_sequences(bcftools_output, genome_id, region):

    bcftools_output = ''
    variants = []

    for line in bcftools_output.splitlines():
        if line.startswith("#"):
            continue
        parts = line.strip().split("\t")
        if len(parts) < 8:
            continue
        chrom_v, pos_v, id_v, ref_v, alt_v, qual_v, filter_v, info_v = parts[:8]
        sample_data = parts[9:]

        has_variant = any(not data.startswith("0/0") for data in sample_data)

        if has_variant:
            effect_type = "."
            gene_id = "."
            if info_v.startswith("ANN="):
                try:
                    _, content = info_v.split("=", 1)
                    items = content.split("|")
                    if len(items) >= 2:
                        effect_type = items[0].replace("_", " ")
                        gene_id = items[1]
                except Exception:
                    pass
            variants.append({
                "CHROM": chrom_v,
                "POS": int(pos_v),
                "ID": id_v,
                "REF": ref_v,
                "ALT": alt_v,
                "QUAL": qual_v,
                "FILTER": filter_v,
                "EFFECT_TYPE": effect_type,
                "GENEID": gene_id,
                "SAMPLES": dict(zip(s.split(",") if s else [], sample_data))
            })



        '''
            genome_id, region
            get reference sequence according to genome_id and region 
            
            fasta_file = f"{vcf}.fa.gz"
            samtools_cmd = ["samtools", "faidx", fasta_file, region]
            reference_seq = run_cmd(samtools_cmd)
        '''

        reference_seq = '''> (Cla97Chr04:15441823-15442823)
GCGAGCGATATTCATTCTCAGGTCGCTATCAGTTATCTCCACCATTAATTGGCGAGAATATGGAGCCATCTTCCAACTGTGGACGCTGACAAACTCCCAATCTTCTTCAA
TTCCCCTAATTCCATCTCTTGGAGAACAGTGGCCGGCGAAGTCACTTCGTCCAAATTGGGACTCGTCATTCGCGCTCCACATCCCTCCAATCCATAACAACCAAATGGAG
CTCCTTCCCGTCCTCAGGTTCGCCTCCAAACACACGCCTCTTCATGTTTTAATCACTGAATTCCATTGAAGTTATCCCTGTTCTTCTGGAGTTCTTGGGGATTTGTTGAA
ATTTTTGAGCACCCCATTTCGATTCTTCATCTATTGGTTTATTACTTAGGTTTGTTTGAGATTTCTGGATATTGGGTCTCTGTAGGGATTCCCTTTTTGACTTTGCTGAT
AATTCTGTTTCTGTTGCTCTCTGTAGTTTCATTTGTTTGTTGTAAATCCATGGATACTTTACTTAAAATCAATAACAAGTATGGTTTTCTGCAACCATTACATGGG
GTTTCGGAAAAAGTGAGTGGTGTGAGGAGTACAAAGTTTCAGAGTCAGGAATTTGGGTTTGGTCATAGGAAGGGTCGTCTGAAATGGAGGAAAGGGGGTTGTCTTAATGT
GAGAAGTAGTTCTCTTTTGGAGCTTGTTCCTGAAACCAAGAAGGAGAATCTTGAGGTTGAACTTCCCATGTATGATCCTTCGAAGGGCCTTGTTGTCGATCTTGCGGTCG
TGGGAGGCGGCCCAGCAGGGCTTGCTGTTGCGCAACAGGTTTCAGAGGCAGGGCTTTCAGTTTGTGCAATTGACCCATCTCCCAAGTTGATTTGGCCCAACAATTATGGG
GTTTGGGTGGATGAATTTGAGGCAATGGATTTGCTAGATTGTCTCGACACGACTTGGTCTGGTGCTGTCGTGTTCACCAATGAGCAATCAACAAAAGATCTTGCTCGACC
TTATGCGAGGGTTAA'''


        # Check if reference sequence exists and is not empty
        if reference_seq is None or not reference_seq.strip():
            raise ValueError("No reference sequence found or sequence is empty")
            
        else:
            header_match = re.match(r">.*\n", reference_seq)
            header = header_match.group(0).strip() if header_match else ""
            seq_lines = reference_seq[header_match.end():].replace("\n", "")

            seq_list = list(seq_lines)
            for var in variants:
                offset = var["POS"] - start
                if 0 <= offset < len(seq_list):
                    ref = var["REF"]
                    alt = var["ALT"]
                    is_center = (var["POS"] == center_pos)
                    is_indel = len(ref) != len(alt)

                    if is_indel:
                        if len(ref) > len(alt):
                            tag = f"-{ref[1:]}" if len(ref) > 1 else "-X"
                        else:
                            tag = f"+{alt[1:]}" if len(alt) > 1 else "+X"

                        marker = f"{{{tag}}}" if is_center else tag
                    else:
                        marker = f"[[{ref}|{alt}]]" if is_center else f"[{ref}|{alt}]"

                    seq_list[offset] = marker

            marked_seq = "".join(seq_list)

            def wrap_seq(s: str, width=60):
                return "\n".join(s[i:i+width] for i in range(0, len(s), width))

            full_marked_seq = f">{chrom}_{center_pos} ({region})\n{wrap_seq(marked_seq)}"
            simple_seq = f">{header}\n{wrap_seq(seq_lines)}"

            # 查找中心位置的变异
            target_var = next((v for v in variants if v["POS"] == center_pos), None)

            # 构建 TARGET_INFO，默认值为 "-"
            target_info = {
                "CHROM_POS": f"{chrom}:{center_pos}",
                "REF_ALT": "-",
                "EFFECT_TYPE": "-",
                "GENEID": "-"
            }

            if target_var:
                target_info.update({
                    "REF_ALT": f"{target_var['REF']}/{target_var['ALT']}",
                    "EFFECT_TYPE": target_var["EFFECT_TYPE"],
                    "GENEID": target_var["GENEID"]
                })

            output = {
                "VARIANTS": variants,
                "REFERENCE_SEQUENCE": simple_seq,
                "MARKED_SEQUENCE": full_marked_seq,
                "TARGET_INFO": target_info
            }

            return output
