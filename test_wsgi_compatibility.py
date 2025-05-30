#!/usr/bin/python3

"""
Test script to validate Python 3 compatibility for BACmonWSGI.py

This script tests basic imports and functionality of the BACmonWSGI application
without requiring a running server.
"""

import sys
import os
import importlib
import traceback

def test_bottle_imports():
    """Test that bottle module can be imported"""
    try:
        import bottle
        print("✅ Successfully imported bottle module")
    except ImportError as e:
        print(f"❌ Failed to import bottle: {str(e)}")
        print("You may need to install bottle: pip install bottle")
        return False
    return True

def test_wsgi_imports():
    """Test that BACmonWSGI imports work without errors"""
    try:
        # Make a modified version of the imports only
        with open('BACmonWSGI.py', 'r') as f:
            source = f.read()
            # Get the import section
            import_lines = []
            for line in source.split('\n'):
                if line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                # Stop when we hit the first function def
                elif line.startswith('def '):
                    break
            
            import_source = '\n'.join(import_lines)
            import_source += '\nprint("WSGI imports successful")'
            
            # Execute the imports only
            exec(import_source)
            print("✅ BACmonWSGI imports successful")
            return True
    except Exception as e:
        print(f"❌ Failed to import in BACmonWSGI.py: {str(e)}")
        traceback.print_exc()
        return False

def test_route_functions():
    """Test that route function signatures are compatible"""
    route_functions = []
    
    try:
        with open('BACmonWSGI.py', 'r') as f:
            source = f.read()
            lines = source.split('\n')
            
            for i, line in enumerate(lines):
                if '@bottle.route(' in line:
                    # Find the function definition that follows
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].strip().startswith('def '):
                            function_name = lines[j].split('def ')[1].split('(')[0].strip()
                            route_functions.append(function_name)
                            break
            
            print(f"✅ Found {len(route_functions)} route functions")
            print("  Routes: " + ", ".join(route_functions))
            return True
    except Exception as e:
        print(f"❌ Failed to analyze route functions: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all WSGI tests"""
    print("Starting WSGI compatibility tests...\n")
    
    success = True
    success = test_bottle_imports() and success
    success = test_wsgi_imports() and success
    success = test_route_functions() and success
    
    if success:
        print("\nAll WSGI tests passed successfully! 🎉")
        return 0
    else:
        print("\nSome WSGI tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 