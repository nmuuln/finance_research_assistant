"""File processing utilities for uploaded documents."""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import mimetypes

# PDF processing
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Excel/CSV processing
try:
    import pandas as pd
except ImportError:
    pd = None


class FileProcessor:
    """Process uploaded files and extract content."""

    SUPPORTED_TYPES = {
        'application/pdf': ['.pdf'],
        'text/csv': ['.csv'],
        'application/vnd.ms-excel': ['.xls'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'text/plain': ['.txt'],
    }

    @staticmethod
    def get_file_type(filename: str) -> Optional[str]:
        """Determine file type from filename."""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if file type is supported."""
        file_type = FileProcessor.get_file_type(filename)
        return file_type in FileProcessor.SUPPORTED_TYPES

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
        """Extract text content from PDF."""
        if not PdfReader:
            return {
                'success': False,
                'error': 'pypdf not installed. Run: pip install pypdf'
            }

        try:
            reader = PdfReader(file_path)
            text_parts = []
            metadata = {
                'num_pages': len(reader.pages),
                'metadata': reader.metadata if hasattr(reader, 'metadata') else {}
            }

            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"--- Page {i + 1} ---\n{text}")

            full_text = "\n\n".join(text_parts)

            return {
                'success': True,
                'content': full_text,
                'metadata': metadata,
                'char_count': len(full_text),
                'page_count': len(reader.pages)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'PDF extraction failed: {str(e)}'
            }

    @staticmethod
    def extract_data_from_excel(file_path: str, max_rows: int = 1000) -> Dict[str, Any]:
        """Extract data from Excel/CSV file."""
        if not pd:
            return {
                'success': False,
                'error': 'pandas not installed. Run: pip install pandas openpyxl'
            }

        try:
            # Determine file extension
            ext = Path(file_path).suffix.lower()

            if ext == '.csv':
                df = pd.read_csv(file_path, nrows=max_rows)
                sheets = {'Sheet1': df}
            else:
                # Read Excel file (supports .xls and .xlsx)
                excel_file = pd.ExcelFile(file_path)
                sheets = {}
                for sheet_name in excel_file.sheet_names[:5]:  # Max 5 sheets
                    sheets[sheet_name] = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=max_rows)

            # Convert to structured text
            text_parts = []
            for sheet_name, df in sheets.items():
                text_parts.append(f"=== {sheet_name} ===")
                text_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
                text_parts.append(f"Rows: {len(df)}")
                text_parts.append("\nData Summary:")

                # Add summary statistics for numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    summary = df[numeric_cols].describe()
                    text_parts.append(summary.to_string())

                # Add first few rows as context
                text_parts.append("\nFirst 10 rows:")
                text_parts.append(df.head(10).to_string())

            full_text = "\n\n".join(text_parts)

            return {
                'success': True,
                'content': full_text,
                'metadata': {
                    'sheets': list(sheets.keys()),
                    'total_rows': sum(len(df) for df in sheets.values()),
                    'columns': {name: df.columns.tolist() for name, df in sheets.items()}
                },
                'char_count': len(full_text),
                'sheet_count': len(sheets)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Excel/CSV extraction failed: {str(e)}'
            }

    @staticmethod
    def extract_text_from_file(file_path: str) -> Dict[str, Any]:
        """Extract text from plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'success': True,
                'content': content,
                'metadata': {
                    'encoding': 'utf-8'
                },
                'char_count': len(content)
            }

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()

                return {
                    'success': True,
                    'content': content,
                    'metadata': {
                        'encoding': 'latin-1'
                    },
                    'char_count': len(content)
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Text extraction failed: {str(e)}'
                }

    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        """Process uploaded file and extract content based on type."""
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found'
            }

        filename = os.path.basename(file_path)
        file_type = FileProcessor.get_file_type(filename)

        if not FileProcessor.is_supported(filename):
            return {
                'success': False,
                'error': f'Unsupported file type: {file_type}'
            }

        # Route to appropriate processor
        if file_type == 'application/pdf':
            result = FileProcessor.extract_text_from_pdf(file_path)
        elif file_type in ['text/csv', 'application/vnd.ms-excel',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            result = FileProcessor.extract_data_from_excel(file_path)
        elif file_type == 'text/plain':
            result = FileProcessor.extract_text_from_file(file_path)
        else:
            return {
                'success': False,
                'error': f'No processor available for: {file_type}'
            }

        # Add common metadata
        if result.get('success'):
            result['file_type'] = file_type
            result['filename'] = filename
            result['file_size'] = os.path.getsize(file_path)

        return result


def summarize_file_content(content: str, max_chars: int = 5000) -> str:
    """Summarize file content for research context."""
    if len(content) <= max_chars:
        return content

    # Take first part and indicate truncation
    truncated = content[:max_chars]
    return f"{truncated}\n\n... [Content truncated, {len(content) - max_chars} characters omitted] ..."
