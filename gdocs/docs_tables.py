"""
Google Docs Table Operations

This module provides utilities for creating and manipulating tables
in Google Docs, including population with data and formatting.
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def extract_table_as_data(table_info: Dict[str, Any]) -> List[List[str]]:
    """
    Extract table content as a 2D array of strings.

    Args:
        table_info: Table information from document structure

    Returns:
        2D list of cell contents
    """
    data = []
    cells = table_info.get("cells", [])

    for row in cells:
        row_data = []
        for cell in row:
            row_data.append(cell.get("content", "").strip())
        data.append(row_data)

    return data


def validate_table_data(data: List[List[str]]) -> Tuple[bool, str]:
    """
    Validates table data format and provides specific error messages for LLMs.

    WHAT THIS CHECKS:
    - Data is a 2D list (list of lists)
    - All rows have consistent column counts
    - Dimensions are within Google Docs limits
    - No None or undefined values

    VALID FORMAT EXAMPLE:
    [
        ["Header1", "Header2"],     # Row 0 - 2 columns
        ["Data1", "Data2"],        # Row 1 - 2 columns
        ["Data3", "Data4"]         # Row 2 - 2 columns
    ]

    INVALID FORMATS:
    - [["col1"], ["col1", "col2"]]  # Inconsistent column counts
    - ["col1", "col2"]              # Not 2D (missing inner lists)
    - [["col1", None]]              # Contains None values
    - [] or [[]]                    # Empty data

    Args:
        data: 2D array of data to validate

    Returns:
        Tuple of (is_valid, error_message_with_examples)
    """
    if not data:
        return (
            False,
            "Data is empty. Use format: [['col1', 'col2'], ['row1col1', 'row1col2']]",
        )

    if not isinstance(data, list):
        return (
            False,
            f"Data must be a list, got {type(data).__name__}. Use format: [['col1', 'col2'], ['row1col1', 'row1col2']]",
        )

    if not all(isinstance(row, list) for row in data):
        return (
            False,
            f"Data must be a 2D list (list of lists). Each row must be a list. Check your format: {data}",
        )

    # Check for consistent column count
    col_counts = [len(row) for row in data]
    if len(set(col_counts)) > 1:
        return (
            False,
            f"All rows must have same number of columns. Found: {col_counts}. Fix your data format.",
        )

    # Check for reasonable size
    rows = len(data)
    cols = col_counts[0] if col_counts else 0

    if rows > 1000:
        return False, f"Too many rows ({rows}). Google Docs limit is 1000 rows."

    if cols > 20:
        return False, f"Too many columns ({cols}). Google Docs limit is 20 columns."

    return True, f"Valid table data: {rows}x{cols} table format"
