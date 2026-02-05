# Test Data Directory

This directory contains test data used across all services for integration and end-to-end testing.

## Structure

```
test_data/
├── documents/          # Sample documents for RAG/document processing tests
├── fixtures/           # JSON/YAML test fixtures
└── schemas/            # JSON schemas for API validation
```

## Usage

### In Python Tests

```python
from pathlib import Path

# Get test data root (from any service)
TEST_DATA_ROOT = Path(__file__).parent.parent.parent.parent / "test_data"
DOCUMENT_PATH = TEST_DATA_ROOT / "documents" / "registration.txt"
```

### In Shell Scripts

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DATA_DIR="${SCRIPT_DIR}/test_data"
DOCUMENT="${TEST_DATA_DIR}/documents/registration.txt"
```

## Guidelines

- **Keep files small** (< 10MB) - use fixtures for larger test scenarios
- **Use descriptive names** - e.g., `registration.txt` not `test1.txt`
- **Document purpose** - add comments in test files explaining what data is used
- **Version control** - commit essential test documents
- **No sensitive data** - never commit credentials, PII, or production data

## Adding New Test Data

1. Place documents in appropriate subdirectory
2. Use descriptive, lowercase filenames with extensions
3. Update this README if adding new categories
4. Ensure files are < 10MB (use fixtures for larger data)

## Current Test Data

### Documents
- `registration.txt` - Sample registration/enrollment document for RAG testing
