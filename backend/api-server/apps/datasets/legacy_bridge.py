from apps.databases.crud import database_db, database_file_db, database_meta_db, project_database_db


class DatasetLegacyBridge:
    def get_database(self, db, dataset_id):
        return database_db.get(db=db, id=dataset_id)

    def list_databases(self, db, page=0, size=0, filters=None, filters_exp=None, sort="-id"):
        return database_db.get_list(
            db=db,
            page=page,
            size=size,
            filters=filters or {},
            filters_exp=filters_exp or [],
            sort=sort,
        )

    def create_database(self, db, obj_in):
        return database_db.create_one(db=db, obj_in=obj_in)

    def update_database(self, db, db_obj, obj_in):
        return database_db.update_one(db=db, db_obj=db_obj, obj_in=obj_in)

    def get_primary_file(self, db, dataset_id):
        return database_file_db.get_filter(db=db, filters={"database_id": dataset_id})

    def create_primary_file(self, db, obj_in):
        return database_file_db.create_one(db=db, obj_in=obj_in)

    def update_primary_file(self, db, db_obj, obj_in):
        return database_file_db.update_one(db=db, db_obj=db_obj, obj_in=obj_in)

    def list_meta(self, db, dataset_id):
        return database_meta_db.get_data(db=db, filters={"database_id": dataset_id})

    def list_project_links_by_dataset(self, db, dataset_id):
        return project_database_db.get_data(db=db, filters={"database_id": dataset_id})

    def list_project_links_by_project(self, db, project_id):
        return project_database_db.get_data(db=db, filters={"project_id": project_id})

    def create_project_link(self, db, obj_in):
        return project_database_db.create_one(db=db, obj_in=obj_in)

    def delete_legacy_cascade(self, db, dataset_id):
        """Cascade-delete all legacy database records for a dataset.

        Deletes from ProjectDatabasesLink, DatabasesMeta, DatabasesFile, and
        Databases -- in the correct order to avoid FK violations.
        Does NOT commit the transaction; the caller must do that.
        """
        db.query(project_database_db.model).filter(
            project_database_db.model.database_id == dataset_id
        ).delete(synchronize_session=False)
        db.query(database_meta_db.model).filter(
            database_meta_db.model.database_id == dataset_id
        ).delete(synchronize_session=False)
        db.query(database_file_db.model).filter(
            database_file_db.model.database_id == dataset_id
        ).delete(synchronize_session=False)
        db.query(database_db.model).filter(
            database_db.model.id == dataset_id
        ).delete(synchronize_session=False)


dataset_legacy_bridge = DatasetLegacyBridge()
