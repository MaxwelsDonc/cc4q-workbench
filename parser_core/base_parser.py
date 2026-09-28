from abc import ABC, abstractmethod
from typing import List
from parser_core.types import CommentRecord

class BaseParser(ABC):

    @abstractmethod
    def extract_comment_pairs(self, file_path: str) -> List[CommentRecord]:
        pass
