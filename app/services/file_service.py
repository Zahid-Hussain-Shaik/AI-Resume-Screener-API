import io
import logging

from pypdf import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


class FileService:
    """Service for processing and extracting text from various file formats."""

    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Extract text from a PDF file."""
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error("Failed to extract text from PDF: %s", e)
            raise ValueError(f"Could not read PDF file: {str(e)}")

    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        """Extract text from a DOCX file."""
        try:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error("Failed to extract text from DOCX: %s", e)
            raise ValueError(f"Could not read DOCX file: {str(e)}")

    @classmethod
    def extract_text(cls, file_content: bytes, filename: str) -> str:
        """Extract text based on file extension."""
        ext = filename.lower().split(".")[-1]
        if ext == "pdf":
            return cls.extract_text_from_pdf(file_content)
        elif ext in ["docx", "doc"]:
            return cls.extract_text_from_docx(file_content)
        elif ext == "txt":
            return file_content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported file format: {ext}")
