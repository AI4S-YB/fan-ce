import os
from basis.core.genome_utils import process_genome_files
from apps.databases.crud import database_db,database_file_db
from basis.core.expression_utils import process_rnaseq_file
from basis.core.variant_utils import process_variant_file
from basis.core.samtools_utils import process_sequence
from basis.core.feature_utils import process_tabix_file
from basis.core.phenome_utils import process_phenome_file
from basis.core.germplasm_utils import load_graph_from_xls

def database_format(db,database_obj):
    file_path = database_obj.file.path
    if database_obj.type == '1':
        try:
            process_genome_files('task_id', database_obj.file.path, 'request.operation')
            database_db.update_one(db=db,db_obj=database_obj,obj_in={'status':4})
        except Exception as e:
            database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 7})
    elif database_obj.type == '2':
        output_h5_file = process_rnaseq_file( database_obj.file.path)
        database_file_db.get_one(db=db,id=database_obj.file.id)
        database_file_db.update_one(db=db,db_obj=database_obj,obj_in={'path':output_h5_file})
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '3':
        process_variant_file(database_obj.file.path)
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '4':
        process_tabix_file(database_obj.file.path, '')
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '5':
        processed_path = process_sequence(database_obj.file.path)
        database_file_db.get_one(db=db, id=database_obj.file.id)
        database_file_db.update_one(db=db, db_obj=database_obj, obj_in={'path': processed_path})
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '6':
        process_sequence(database_obj.file.path)
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '8':
        base_path = os.path.splitext(database_obj.file.path)[0]
        process_phenome_file(database_obj.file.path, f"{base_path}.db")
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
    elif database_obj.type == '7':
        base_path = os.path.splitext(database_obj.file.path)[0]
        load_graph_from_xls(file_path,3,4)
        database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 4})
