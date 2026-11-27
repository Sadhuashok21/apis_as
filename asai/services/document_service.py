import os
import csv
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Tuple


class DocumentService:
    """
    Extracts text and metadata from PDF, DOCX, CSV, XLSX, and TXT files.
    """

    @staticmethod
    def extract_text_from_file(file_path: str, file_type: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extracts clean plain text from the given document file path.
        Returns (extracted_text, metadata_dict).
        """
        path = Path(file_path)
        if not path.exists():
            return "", {"error": "File does not exist"}

        clean_type = file_type.upper().strip().lstrip(".")
        metadata: Dict[str, Any] = {
            "file_size": path.stat().st_size,
            "filename": path.name,
            "file_type": clean_type
        }

        try:
            if clean_type == "PDF":
                return DocumentService._extract_pdf(path, metadata)
            elif clean_type in ("DOCX", "DOC"):
                return DocumentService._extract_docx(path, metadata)
            elif clean_type == "CSV":
                return DocumentService._extract_csv(path, metadata)
            elif clean_type in ("XLSX", "XLS"):
                return DocumentService._extract_xlsx(path, metadata)
            else:
                return DocumentService._extract_txt(path, metadata)
        except Exception as e:
            return f"Error extracting document text: {str(e)}", {"error": str(e)}

    @staticmethod
    def _extract_pdf(path: Path, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        # 1. Try PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(path))
            metadata["pages"] = len(doc)
            pages_text = []
            for i in range(min(len(doc), 50)): # Extract up to first 50 pages
                text = doc[i].get_text()
                if text.strip():
                    pages_text.append(f"--- Page {i+1} ---\n{text}")
            doc.close()
            full_text = "\n\n".join(pages_text)
            metadata["char_count"] = len(full_text)
            return full_text, metadata
        except ImportError:
            pass

        # 2. Try pypdf / fallback plain read
        try:
            with open(path, "rb") as f:
                content = f.read()
            # Basic textual scan
            strings = [s.decode("latin-1") for s in content.split(b"\n") if b"BT" in s or b"ET" in s or len(s) > 20]
            preview = "\n".join(strings[:200])
            metadata["pages"] = 1
            metadata["char_count"] = len(preview)
            return preview, metadata
        except Exception as e:
            return f"PDF reading error: {str(e)}", metadata

    @staticmethod
    def _extract_docx(path: Path, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        # Fast, zero-dependency XML parsing of standard DOCX zip format
        try:
            with zipfile.ZipFile(str(path)) as docx:
                xml_content = docx.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            # Word namespaces
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for p in tree.findall(".//w:p", ns):
                texts = [node.text for node in p.findall(".//w:t", ns) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            full_text = "\n\n".join(paragraphs)
            metadata["paragraphs"] = len(paragraphs)
            metadata["char_count"] = len(full_text)
            return full_text, metadata
        except Exception as e:
            return f"DOCX extraction error: {str(e)}", metadata

    @staticmethod
    def _extract_csv(path: Path, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        lines = []
        row_count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    lines.append("Columns: " + ", ".join(headers))
                    metadata["columns"] = headers
                for row in reader:
                    row_count += 1
                    if row_count <= 200: # first 200 rows for LLM context
                        lines.append(", ".join(row))
            metadata["row_count"] = row_count
            full_text = "\n".join(lines)
            metadata["char_count"] = len(full_text)
            return full_text, metadata
        except Exception as e:
            return f"CSV extraction error: {str(e)}", metadata

    @staticmethod
    def _extract_xlsx(path: Path, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        # Try pandas / openpyxl
        try:
            import pandas as pd
            excel = pd.read_excel(str(path), sheet_name=None)
            sheet_summaries = []
            for sheet_name, df in excel.items():
                sheet_summaries.append(f"Sheet: {sheet_name} ({len(df)} rows, {len(df.columns)} columns)")
                sheet_summaries.append(df.head(50).to_string())
            full_text = "\n\n".join(sheet_summaries)
            metadata["sheets"] = list(excel.keys())
            metadata["char_count"] = len(full_text)
            return full_text, metadata
        except Exception:
            # Fallback text summary
            return f"Excel spreadsheet: {path.name}", metadata

    @staticmethod
    def _extract_txt(path: Path, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(500000) # up to ~500KB
            metadata["char_count"] = len(text)
            return text, metadata
        except Exception as e:
            return f"TXT extraction error: {str(e)}", metadata


document_service = DocumentService()
