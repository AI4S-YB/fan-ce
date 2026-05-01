
from apps.databases.crud import project_database_db
from apps.system.team.crud import team_db,team_project_db

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
    def get_database_file_path(db,team_id):
        team_obj = team_db.get_one(db=db,id=team_id)
        if team_obj:
            return team_obj.database_path
        return ''

    @staticmethod
    def create_database(db,database_id,project_id):
        project_database_db.create_batch(db=db,add_data={"database_id":database_id,'project_id':project_id})

databases_service = DatabasesService()