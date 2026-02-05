# Test Structure and CI/CD Recommendations

## Recommended Repository Structure

```
enrollment-assistant/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Main CI/CD pipeline
│       ├── test-unit.yml            # Unit tests only
│       └── test-integration.yml     # Integration tests
│
├── backend/
│   ├── services/
│   │   ├── agent_ai/
│   │   │   ├── tests/               # Service-specific unit tests
│   │   │   │   ├── unit/            # Unit tests
│   │   │   │   ├── integration/     # Integration tests
│   │   │   │   └── conftest.py
│   │   │   └── ...
│   │   │
│   │   └── rag_api/
│   │       ├── tests/               # Service-specific unit tests
│   │       │   ├── unit/            # Unit tests
│   │       │   ├── integration/     # Integration tests
│   │       │   └── conftest.py
│   │       └── ...
│   │
│   └── shared/                      # Shared code between services
│
├── tests/                           # Cross-service & E2E tests
│   ├── unit/                        # Cross-service unit tests
│   ├── integration/                 # Integration tests
│   ├── e2e/                         # End-to-end tests
│   ├── fixtures/                    # Shared test fixtures
│   └── conftest.py                  # Shared pytest config
│
├── test_data/                       # Test data (version controlled)
│   ├── documents/                   # Sample documents for RAG testing
│   │   ├── registration.txt
│   │   ├── enrollment_policy.pdf
│   │   └── course_catalog.txt
│   ├── schemas/                     # JSON schemas for validation
│   └── fixtures/                    # Test fixtures (JSON, YAML)
│
├── scripts/                         # Test scripts
│   ├── test_basic_api.sh
│   ├── test_rag_integration.sh
│   └── run_all_tests.sh
│
└── infrastructure/
    └── docker/
        ├── docker-compose.yml
        └── docker-compose.test.yml   # Test-specific compose file
```

## Test Data Organization

### Current Location: `backend/test/data/`
**Issue**: Test data is mixed with backend code, making it harder to:
- Share test data across services
- Use in CI/CD pipelines
- Keep test data version controlled separately

### Recommended Location: `test_data/` (root level)

**Benefits:**
- ✅ Clear separation of test data from source code
- ✅ Easy to reference in CI/CD pipelines
- ✅ Can be shared across all services
- ✅ Clear what's test data vs production data
- ✅ Easier to manage test data lifecycle

## Migration Plan

### Step 1: Create New Structure
```bash
mkdir -p test_data/documents
mkdir -p tests/{unit,integration,e2e,fixtures}
```

### Step 2: Move Test Data
```bash
# Move existing test data
mv backend/test/data/registration.txt test_data/documents/
rm -rf backend/test/data
```

### Step 3: Update References
- Update test scripts to reference `test_data/`
- Update CI/CD workflows
- Update documentation

## Test Data Guidelines

### What Should Be in `test_data/`?

✅ **Include:**
- Sample documents (PDFs, TXT, etc.) for RAG testing
- Small, anonymized test datasets
- JSON schemas for API validation
- Mock responses for testing
- Test fixtures (small files < 1MB)

❌ **Exclude:**
- Large files (> 10MB) - use fixtures or generate programmatically
- Sensitive data (credentials, PII)
- Generated test data (use fixtures instead)
- Binary files that change frequently

### File Naming Conventions

```
test_data/
├── documents/
│   ├── registration.txt              # Descriptive name
│   ├── enrollment_policy_2024.pdf   # Include version/year if relevant
│   └── course_catalog_sample.txt    # Use "sample" for partial data
│
└── fixtures/
    ├── user_registration.json        # JSON fixtures
    ├── chat_session.yaml            # YAML fixtures
    └── api_responses/                # Organized by type
        ├── auth_success.json
        └── chat_response.json
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Unit Tests
        run: |
          cd backend/services/rag_api
          pytest tests/unit/ -v
      
      - name: Run Integration Tests
        run: |
          cd backend/services/rag_api
          pytest tests/integration/ -v
          # Test data available at ../../test_data/
      
      - name: Run E2E Tests
        run: |
          pytest tests/e2e/ -v
          # Uses test_data/ for document uploads
```

### Docker Compose for Testing

```yaml
# infrastructure/docker/docker-compose.test.yml
version: '3.8'

services:
  test_rag_api:
    build: ../../backend/services/rag_api
    volumes:
      - ../../test_data:/app/test_data:ro  # Mount test data read-only
    environment:
      - TEST_MODE=true
    command: pytest tests/integration/ -v
```

## Usage Examples

### In Python Tests

```python
# backend/services/rag_api/tests/integration/test_rag_upload.py
import os
from pathlib import Path

# Get test data path (works from any service)
TEST_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "test_data"
REGISTRATION_DOC = TEST_DATA_DIR / "documents" / "registration.txt"

def test_upload_registration_document():
    with open(REGISTRATION_DOC, 'rb') as f:
        response = client.post("/embed", files={"file": f})
    assert response.status_code == 200
```

### In Test Scripts

```bash
# scripts/test_rag_integration.sh
TEST_DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/test_data"
REGISTRATION_FILE="${TEST_DATA_DIR}/documents/registration.txt"

curl -X POST http://localhost:8010/embed \
  -F "file_id=test-registration" \
  -F "file=@${REGISTRATION_FILE}"
```

## .gitignore Updates

```gitignore
# Test data - keep structure, ignore generated files
test_data/**/*.tmp
test_data/**/*.cache
test_data/generated/

# But DO commit:
# test_data/documents/*.txt
# test_data/fixtures/*.json
```

## Best Practices

1. **Keep test data small**: Prefer fixtures over large files
2. **Version control test data**: Commit essential test documents
3. **Use relative paths**: Make tests portable
4. **Document test data**: Add README.md in test_data/
5. **Separate by purpose**: documents/, fixtures/, schemas/
6. **CI/CD friendly**: Structure should work in containers

## Migration Checklist

- [ ] Create `test_data/` directory structure
- [ ] Move `backend/test/data/registration.txt` to `test_data/documents/`
- [ ] Update test scripts to use new paths
- [ ] Update CI/CD workflows
- [ ] Update `.gitignore` if needed
- [ ] Add `test_data/README.md` documenting test data
- [ ] Update service-specific test files to reference new paths
- [ ] Remove old `backend/test/` directory
