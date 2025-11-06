"""
File Service for CSV processing.
Handles CSV validation, parsing, and conversion to domain models.
"""
import csv
import io
from typing import List, BinaryIO
from src.models.drug_model import Drug
from src.core.exceptions import CSVProcessingException, ValidationException


class FileService:
    """Service for file processing operations."""
    
    REQUIRED_COLUMNS = {'drug_name', 'target', 'efficacy'}
    
    def validate_csv_structure(self, file: BinaryIO) -> None:
        """
        Validate CSV file structure and headers.
        
        Args:
            file: CSV file to validate
            
        Raises:
            ValidationException: If CSV structure is invalid
        """
        try:
            content = file.read().decode('utf-8')
            file.seek(0)  # Reset file pointer
            
            csv_reader = csv.DictReader(io.StringIO(content))
            headers = set(csv_reader.fieldnames or [])
            
            missing_columns = self.REQUIRED_COLUMNS - headers
            if missing_columns:
                raise ValidationException(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )
                
        except UnicodeDecodeError as e:
            raise ValidationException("File must be a valid UTF-8 encoded CSV") from e
        except Exception as e:
            raise CSVProcessingException(f"Failed to validate CSV structure: {str(e)}") from e
    
    def parse_csv_to_drugs(self, file: BinaryIO) -> List[Drug]:
        """
        Parse CSV file and convert to Drug domain models.
        
        Args:
            file: CSV file to parse
            
        Returns:
            List of Drug objects
            
        Raises:
            CSVProcessingException: If parsing fails
            ValidationException: If data validation fails
        """
        try:
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            drugs = []
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                try:
                    drug = self._row_to_drug(row, row_num)
                    drugs.append(drug)
                except ValidationException as e:
                    raise ValidationException(f"Row {row_num}: {e.message}") from e
            
            if not drugs:
                raise ValidationException("CSV file is empty or contains no valid data")
            
            return drugs
            
        except ValidationException:
            raise
        except Exception as e:
            raise CSVProcessingException(f"Failed to parse CSV file: {str(e)}") from e
    
    def _row_to_drug(self, row: dict, row_num: int) -> Drug:
        """
        Convert CSV row to Drug domain model.
        
        Args:
            row: CSV row as dictionary
            row_num: Row number for error reporting
            
        Returns:
            Drug object
            
        Raises:
            ValidationException: If row data is invalid
        """
        try:
            drug_name = row.get('drug_name', '').strip()
            target = row.get('target', '').strip()
            efficacy_str = row.get('efficacy', '').strip()
            
            # Validate required fields
            if not drug_name:
                raise ValidationException("drug_name cannot be empty")
            if not target:
                raise ValidationException("target cannot be empty")
            if not efficacy_str:
                raise ValidationException("efficacy cannot be empty")
            
            # Parse and validate efficacy
            try:
                efficacy = float(efficacy_str)
            except ValueError:
                raise ValidationException(f"efficacy must be a number, got: {efficacy_str}")
            
            if not 0 <= efficacy <= 100:
                raise ValidationException(f"efficacy must be between 0 and 100, got: {efficacy}")
            
            return Drug(
                drug_name=drug_name,
                target=target,
                efficacy=efficacy
            )
            
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Invalid data: {str(e)}") from e
