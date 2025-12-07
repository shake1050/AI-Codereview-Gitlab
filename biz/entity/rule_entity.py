"""审查规则实体类"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RuleEntity:
    """审查规则实体"""
    id: Optional[int] = None
    rule_key: str = ""
    system_prompt: str = ""
    user_prompt: str = ""
    description: Optional[str] = None
    is_active: bool = True
    created_at: int = 0
    updated_at: int = 0
    updated_by: Optional[str] = None


@dataclass
class RuleHistoryEntity:
    """规则历史记录实体"""
    id: Optional[int] = None
    rule_id: int = 0
    rule_key: str = ""
    system_prompt_old: Optional[str] = None
    system_prompt_new: Optional[str] = None
    user_prompt_old: Optional[str] = None
    user_prompt_new: Optional[str] = None
    change_type: str = ""  # 'create', 'update', 'delete'
    changed_at: int = 0
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
