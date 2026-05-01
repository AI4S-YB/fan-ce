class ProjectService:
    """Community Edition: team functionality removed. All methods are no-ops."""

    @staticmethod
    def get_project_by_team(db, team_id):
        """团队功能已移除，返回空列表"""
        return []

    @staticmethod
    def create_project(db, project_id, team_id=None):
        """团队功能已移除，不做任何操作"""
        pass

    @staticmethod
    def update_project(db, team_id, project_id):
        pass

    @staticmethod
    def delete_project(db, project_id, team_id=None):
        """团队功能已移除，不做任何操作"""
        pass


class TeamService:
    """Community Edition: team functionality removed."""

    @staticmethod
    def get_team_by_user(db, user_id, user):
        """团队功能已移除，返回空列表"""
        return []


class SampleService:
    @staticmethod
    def get_sample_by_project(db, project_id):
        pass


project_service = ProjectService()
team_service = TeamService()
