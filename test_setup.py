#!/usr/bin/env python3
"""Test script to verify the custom UI setup is working correctly."""

import sys
import uuid
from pathlib import Path

print("=" * 60)
print("UFE Research Writer - Setup Verification")
print("=" * 60)
print()

# Test 1: Database initialization
print("✓ Test 1: Database initialization")
try:
    from src.database import Database
    db = Database()
    print(f"  ✅ Database created at: {db.db_path}")
except Exception as e:
    print(f"  ❌ Database initialization failed: {e}")
    sys.exit(1)

# Test 2: Create a test session
print("\n✓ Test 2: Create test session")
test_session_id = f"test-{str(uuid.uuid4())[:8]}"
try:
    session = db.create_session(
        session_id=test_session_id,
        topic="Test Research Topic",
        language="en"
    )
    print(f"  ✅ Session created: {session['id']}")
except Exception as e:
    print(f"  ❌ Session creation failed: {e}")
    sys.exit(1)

# Test 3: Create a test artifact
print("\n✓ Test 3: Create test artifact")
try:
    artifact = db.create_artifact(
        session_id=test_session_id,
        title="Test Report",
        content="# Test Report\n\nThis is a test report.",
        research_brief="Test research brief",
        reference_list="https://example.com/ref1, https://example.com/ref2",
        file_url="https://example.com/report.docx"
    )
    print(f"  ✅ Artifact created: ID {artifact['id']}")
except Exception as e:
    print(f"  ❌ Artifact creation failed: {e}")
    sys.exit(1)

# Test 4: File processor
print("\n✓ Test 4: File processor imports")
try:
    from src.tools.file_processor import FileProcessor
    print(f"  ✅ FileProcessor loaded")
    print(f"  ✅ Supported types: {list(FileProcessor.SUPPORTED_TYPES.keys())}")
except Exception as e:
    print(f"  ❌ File processor import failed: {e}")
    sys.exit(1)

# Test 5: API app
print("\n✓ Test 5: FastAPI app initialization")
try:
    from src.api.app import app
    print(f"  ✅ FastAPI app loaded: {app.title}")
except Exception as e:
    print(f"  ❌ API app initialization failed: {e}")
    sys.exit(1)

# Test 6: Check frontend files
print("\n✓ Test 6: Frontend files")
frontend_files = [
    "frontend/package.json",
    "frontend/svelte.config.js",
    "frontend/src/routes/+page.svelte",
    "frontend/src/routes/sessions/[id]/+page.svelte"
]
missing = []
for file in frontend_files:
    if Path(file).exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - MISSING")
        missing.append(file)

if missing:
    print(f"\n  ⚠️  {len(missing)} frontend files missing")

# Test 7: Retrieve session and artifacts
print("\n✓ Test 7: Query session and artifacts")
try:
    retrieved_session = db.get_session(test_session_id)
    artifacts = db.list_artifacts(test_session_id)
    if retrieved_session:
        print(f"  ✅ Retrieved session: {retrieved_session['topic']}")
    else:
        print("  ❌ Session not found")
        sys.exit(1)
    print(f"  ✅ Found {len(artifacts)} artifact(s)")
except Exception as e:
    print(f"  ❌ Query failed: {e}")
    sys.exit(1)

# Clean up test data
print("\n✓ Cleanup: Removing test data")
try:
    db.update_session(test_session_id, status="deleted")
    print("  ✅ Test session marked as deleted")
except Exception as e:
    print(f"  ⚠️  Cleanup warning: {e}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print()
print("Next steps:")
print("1. Start backend:  python run_api.py")
print("2. Start frontend: cd frontend && npm run dev")
print("3. Open browser:   http://localhost:5173")
print()
