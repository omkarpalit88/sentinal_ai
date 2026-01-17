# SentinAL Test Data

Comprehensive test suite for validating SentinAL's multi-agent detection capabilities across SQL, Terraform, and YAML files.

---

## Test Coverage Matrix

| File Type | Safe | Dangerous | Subtle |
|-----------|------|-----------|--------|
| **SQL** | ✅ 3 files | ✅ 3 files | ✅ 3 files |
| **Terraform** | ✅ 2 files | ✅ 2 files | ✅ 2 files |
| **YAML** | ✅ 2 files | ✅ 2 files | ✅ 2 files |

**Total:** 18 test files across 3 file types and 3 risk categories

---

## Expected Risk Scores

### SQL Files

#### Dangerous
- **drop_table.sql**: 80-100 CRITICAL
  - Patterns: DROP TABLE
  - Findings: 2 CRITICAL

#### Safe
- **select_users.sql**: 0-10 LOW
  - Patterns: None (safe read-only)
  - Findings: 0

#### Subtle
- **delete_no_where.sql**: 40-60 HIGH
  - Patterns: DELETE without WHERE
  - Findings: 2 HIGH
- **implicit_cast.sql**: 10-30 MEDIUM
  - Patterns: Performance anti-patterns
  - Findings: 0-1 MEDIUM (parser detection)

---

### Terraform Files

#### Dangerous
- **force_destroy.tf**: 80-100 CRITICAL
  - Patterns: force_destroy=true, prevent_destroy=false, count=0
  - Findings: 3 (1 CRITICAL, 2 HIGH)
- **destroy_script.tf**: 80-100 CRITICAL
  - Patterns: terraform destroy commands
  - Findings: 3 CRITICAL

#### Safe
- **safe_infrastructure.tf**: 0-10 LOW
  - Patterns: Proper lifecycle blocks
  - Findings: 0

#### Subtle
- **lifecycle_missing.tf**: 20-40 MEDIUM
  - Patterns: Missing prevent_destroy (parser detection)
  - Findings: 1 MEDIUM

---

### YAML Files

#### Dangerous
- **privileged_container.yaml**: 80-100 CRITICAL
  - Patterns: privileged:true, hostNetwork:true, imagePullPolicy:Always
  - Findings: 4 (2 CRITICAL, 2 MEDIUM)
- **zero_replicas.yaml**: 40-60 HIGH
  - Patterns: replicas:0
  - Findings: 1 HIGH

#### Safe
- **safe_deployment.yaml**: 0-10 LOW
  - Patterns: Proper security + resource limits
  - Findings: 0

#### Subtle
- **no_resource_limits.yaml**: 20-40 MEDIUM
  - Patterns: Missing resource limits (parser detection)
  - Findings: 1 MEDIUM

---

## Test Categories Explained

### 🔴 Dangerous
Files with **explicit, high-impact risks** that will cause immediate production incidents:
- Data loss (DROP TABLE, TRUNCATE)
- Infrastructure destruction (terraform destroy, force_destroy)
- Security breaches (privileged containers, host network)
- Service downtime (replicas:0)

### 🟢 Safe
Files with **no detected risks** following best practices:
- Read-only queries
- Proper lifecycle protections
- Security contexts configured
- Resource limits set

### 🟡 Subtle
Files with **implicit or best-practice violations**:
- Missing protections (no prevent_destroy)
- Performance anti-patterns (index misuse)
- Missing configurations (no resource limits)
- Requires context understanding

---

## Multi-Agent Testing

SentinAL's architecture supports analyzing multiple file types in a single deployment:

### Workflow
1. **Upload:** Multiple files (e.g., SQL + Terraform + YAML)
2. **Routing:** Orchestrator routes each file to specialist agent
3. **Analysis:** Each agent analyzes independently
4. **Synthesis:** Findings combined into single Defense Memo
5. **Scoring:** Overall risk = MAX(all file scores)

### Example Multi-File Test
```bash
# Upload 3 files from different types
curl -F "file=@sql/dangerous/drop_table.sql" \
     -F "file=@terraform/dangerous/force_destroy.tf" \
     -F "file=@yaml/dangerous/privileged_container.yaml" \
     http://localhost:8000/api/analyze
```

Expected: 100/100 CRITICAL (highest of 3 files)

---

## File Locations

```
test_data/
├── sql/
│   ├── dangerous/
│   │   ├── drop_table.sql
│   │   └── ...
│   ├── safe/
│   │   └── select_users.sql
│   └── subtle/
│       ├── delete_no_where.sql
│       └── implicit_cast.sql
├── terraform/
│   ├── dangerous/
│   │   ├── force_destroy.tf
│   │   └── destroy_script.tf
│   ├── safe/
│   │   └── safe_infrastructure.tf
│   └── subtle/
│       └── lifecycle_missing.tf
└── yaml/
    ├── dangerous/
    │   ├── privileged_container.yaml
    │   └── zero_replicas.yaml
    ├── safe/
    │   └── safe_deployment.yaml
    └── subtle/
        └── no_resource_limits.yaml
```

---

## Usage

### Manual Testing via UI
1. Start server: `python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2. Open: http://localhost:8000
3. Upload test file
4. Review Defense Memo and risk score

### Automated Testing via API
```bash
# Test dangerous SQL
curl -X POST -F "file=@test_data/sql/dangerous/drop_table.sql" \
     http://localhost:8000/api/analyze

# Test safe Terraform
curl -X POST -F "file=@test_data/terraform/safe/safe_infrastructure.tf" \
     http://localhost:8000/api/analyze

# Test subtle YAML
curl -X POST -F "file=@test_data/yaml/subtle/no_resource_limits.yaml" \
     http://localhost:8000/api/analyze
```

---

## Extending Tests

To add new test cases:

1. **Create file** in appropriate directory (sql/terraform/yaml → dangerous/safe/subtle)
2. **Add patterns** to `backend/config.py` if new risk type
3. **Document** expected risk score and findings in this README
4. **Test manually** via UI or API
5. **Create unit test** in `tests/test_sub_phase_2_4.py`

---

*Last Updated: Phase 2.4 (2026-01-17)*
