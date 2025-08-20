from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ProjectConfig:
    project_name: str
    dependencies: Dict[str, List[str]] | List[str]
    compile: List[str]
