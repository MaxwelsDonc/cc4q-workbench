"""Typed record exchanged between the extraction, segmentation, and
classification stages.

The pipeline serializes these records as JSON objects (one per line in
JSONL outputs). Keeping the shape in one ``TypedDict`` lets static type
checkers and editor tooling follow a record from stage 01 to stage 03.
"""

from typing import List, TypedDict, Union

__all__ = ["CommentRecord"]


class CommentRecord(TypedDict):
    """One comment/code pair (CCP) extracted from a Python file.

    A docstring produces one record for the entire docstring; inline and
    block comments produce one record each. Segmentation (stage 03) later
    splits these records into sentence-level comment units (SCCUs).

    Attributes:
        id: Unique record id assigned by the extraction id generator.
        SDK: SDK name, e.g. ``"qiskit-aer"``.
        version: SDK release or git ref.
        hostLanguage: Source language; currently ``"python"``.
        dirPath: Source path relative to the repository root, split into
            path components.
        comment_type: ``"docstring"``, ``"inline"``, or ``"block"``.
        comment_text: The comment or docstring text.
        code_snippet: Enclosing code context, cleaned according to the
            configured ``clean_mode``.
        code_entity_type: Enclosing scope: ``"module"``, ``"class"``,
            ``"function"``, or ``"file"``.
        comment_line: Inclusive ``[start, end]`` line range of the comment.
        code_line: Inclusive ``[start, end]`` line range of the code
            context.
        extra: Free-form metadata added by later stages (for example the
            docstring segment type).
    """

    id: str
    SDK: str
    version: str
    hostLanguage: str
    dirPath: List[str]
    comment_type: str
    comment_text: str
    code_snippet: str
    code_entity_type: str
    comment_line: List[int]
    code_line: List[int]
    extra: Union[List[Union[str, dict]], dict]
