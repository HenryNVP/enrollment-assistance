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

### Documents
- `registration.txt` - Sample registration/enrollment document for RAG testing
