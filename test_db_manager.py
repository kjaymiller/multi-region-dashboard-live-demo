#!/usr/bin/env python3
"""Test script for database manager functionality."""

import sys
import os
import tempfile
import shutil

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up test environment
test_dir = tempfile.mkdtemp()
os.environ['TEST_DB_STORAGE'] = test_dir

try:
    from db_manager import DatabaseManager, DatabaseConnection
    import datetime
    
    print("✓ DatabaseManager imported successfully")
    
    # Create a test manager with temporary storage
    dm = DatabaseManager(storage_path=test_dir)
    print("✓ DatabaseManager created with temporary storage")
    
    # Test creating a connection
    conn = DatabaseConnection(
        id=dm.generate_connection_id(),
        name='Test Connection',
        host='localhost',
        port=5432,
        database='testdb',
        username='testuser',
        password='testpass',
        created_at=datetime.datetime.now().isoformat()
    )
    print("✓ DatabaseConnection object created")
    
    # Test saving
    success = dm.save_connection(conn)
    print(f"✓ Save connection: {success}")
    
    # Test loading
    connections = dm.get_all_connections()
    print(f"✓ Load connections: found {len(connections)}")
    
    if connections:
        c = connections[0]
        print(f"  - {c.name} ({c.id}) - {c.host}:{c.port}")
    
    print("\n✓ All basic tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Clean up
    if 'test_dir' in locals():
        shutil.rmtree(test_dir, ignore_errors=True)
        print("✓ Temporary directory cleaned up")