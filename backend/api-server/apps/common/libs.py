from apps.system.team.crud import team_db
from sqlalchemy.orm import Session
from fastapi import Depends
from apps.common.depends import get_db

def get_menu_by_team(db:Session = Depends(get_db),team_id:int=-1,user_id:int=-1):
    team = team_db.get(db,team_id)