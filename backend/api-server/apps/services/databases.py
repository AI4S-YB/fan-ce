
from apps.databases.crud import project_database_db

class DatabasesService:
    @staticmethod
    def get_databases_by_project(db,project_id):
        """
        通过项目ID获取数据IDs
        """
        database_ids = [i.database_id for i in project_database_db.get_data(db=db,filters={"project_id":project_id})]
        if database_ids:
            return database_ids
        return []

    @staticmethod
    def get_database_file_path(db):
        """
        Community Edition: 不再使用 team 概念，返回空字符串
        """
        return ''

    @staticmethod
    def create_database(db,database_id,project_id):
        project_database_db.create_batch(db=db,add_data={"database_id":database_id,'project_id':project_id})

databases_service = DatabasesService()