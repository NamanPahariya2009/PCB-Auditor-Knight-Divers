from pydantic import BaseModel
from typing import List, Optional

class Observation(BaseModel):
    components: List[str]
    netlist: List[str]
    current_errors: List[str]

class Action(BaseModel):
    check_type: str 
    target: str

class Reward(BaseModel):
    value: float
    message: str