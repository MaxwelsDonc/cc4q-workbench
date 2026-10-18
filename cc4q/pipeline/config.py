"""YAML configuration loading for the corpus-construction scripts.

A config file pins the repository/project metadata and the input/output
directories used by the build stage. See ``config/examples.yaml`` for a
complete example.
"""

from typing import Any, Dict

import yaml

__all__ = ["read_config"]


def read_config(config_path: str) -> Dict[str, Any]:
    """Read a YAML configuration file.

    Expected keys include ``project``, ``version``, ``language``,
    ``input_dir``, ``output_dir``, ``include_dirs``, ``clean_mode``, and an
    optional ``pipeline`` mapping (``analyze`` / ``segment`` flags).

    Args:
        config_path: Path to a UTF-8 YAML file.

    Returns:
        The parsed configuration mapping.

    Raises:
        FileNotFoundError: If ``config_path`` does not exist.
        yaml.YAMLError: If the file is not valid YAML.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config
