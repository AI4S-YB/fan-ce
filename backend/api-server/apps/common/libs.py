"""
Community Edition: team functionality removed.
"""
from sqlalchemy.orm import Session
from fastapi import Depends
from apps.common.depends import get_db


def get_menu_by_team(db: Session = Depends(get_db), team_id: int = -1, user_id: int = -1):
    """Community Edition: team functionality removed, returns None"""
    return None