from apps.system.team.crud import team_project_db, team_user_role_db


class ProjectService:
    @staticmethod
    def get_project_by_team(db, team_id):
        """
        通过团队ID获取项目IDs
        """
        if team_id:
            project_ids = [i.project_id for i in team_project_db.get_data(db=db, filters={'team_id': team_id})]
            return project_ids
        return []

    @staticmethod
    def create_project(db, team_id, project_id):
        team_project_db.create_batch(db=db, add_data={'project_id': project_id, 'team_id': team_id})

    @staticmethod
    def update_project(db, team_id, project_id):
        pass
    @staticmethod
    def delete_project(db, team_id, project_id):
        team_project_db.remove_batch(db=db, filters={'project_id': project_id, 'team_id': team_id})

class TeamService:
    @staticmethod
    def get_team_by_user(db, user_id, user):
        """
        通过用户ID获取团队IDs
        """
        if user_id:
            team_ids = [i.team_id for i in team_user_role_db.get_data(db=db, filters={'user_id': user_id})]
            return team_ids
        return []


class SampleService:
    @staticmethod
    def get_sample_by_project(db, project_id):
        pass


project_service = ProjectService()
team_service = TeamService()
