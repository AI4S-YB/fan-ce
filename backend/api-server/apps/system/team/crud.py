# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import Any, Dict, Union, Optional, TypeVar
from db.base import CRUDBase
from db.database import Base
from .models import Team,TeamProjectLink,TeamRoleLink,TeamUserLink
from .schemas import CreateModel,UpdateModel

ModelType = TypeVar("ModelType", bound=Base)

class CRUDTeam(CRUDBase[Team, CreateModel, UpdateModel]):
    pass

class CRUDTeamProjectLink(CRUDBase[TeamProjectLink, CreateModel, UpdateModel]):
    pass
class CRUDTeamRoleLink(CRUDBase[TeamRoleLink, CreateModel, UpdateModel]):
    pass
class CRUDTeamUserLink(CRUDBase[TeamUserLink, CreateModel, UpdateModel]):
    pass
team_db = CRUDTeam(Team)
team_project_db = CRUDTeamProjectLink(TeamProjectLink)
team_role_db = CRUDTeamRoleLink(TeamRoleLink)
team_user_db = CRUDTeamUserLink(TeamUserLink)
team_user_role_db = CRUDTeamUserLink(TeamUserLink)