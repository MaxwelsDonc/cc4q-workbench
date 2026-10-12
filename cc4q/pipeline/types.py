from typing import TypedDict, List, Union

class CommentRecord(TypedDict):
    id: str
    SDK: str
    version: str
    hostLanguage: str
    dirPath: str
    comment_type: str
    comment_text: str
    code_snippet: str
    code_entity_type: str
    comment_line: List[int]
    code_line: List[int]
    extra: List[Union[str, dict]]
