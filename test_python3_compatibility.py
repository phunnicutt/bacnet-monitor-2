#!/usr/bin/python3

"""
Python 3 Compatibility Test Script for BACmon

This script tests various aspects of the BACmon codebase to ensure
compatibility with Python 3 after migration from Python 2.
"""

import sys
import os
import importlib
import traceback

# Dictionary to store test results
test_results = {
    "passed": [],
    "failed": []
}

def run_test(test_name, test_func):
    """Run a test and record the result"""
    print(f"Running test: {test_name}")
    try:
        test_func()
        test_results["passed"].append(test_name)
        print(f"✅ {test_name} - PASSED")
        return True
    except Exception as e:
        test_results["failed"].append(test_name)
        print(f"❌ {test_name} - FAILED")
        print(f"   Error: {str(e)}")
        traceback.print_exc()
        return False

def test_import_modules():
    """Test that all main modules can be imported"""
    modules = ['XML', 'XHTML', 'timeutil']
    
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            print(f"  Successfully imported {module_name}")
        except ImportError as e:
            raise ImportError(f"Failed to import {module_name}: {str(e)}")

def test_bacmon_imports():
    """Test that BACmon.py imports work"""
    try:
        # Test only imports, not execution
        with open('BACmon.py', 'r') as f:
            source = f.read()
            # Replace actual execution with just imports
            source = '\n'.join([line for line in source.split('\n') 
                               if line.startswith('import ') or line.startswith('from ')])
            source += '\nprint("Imports successful")'
            # Execute the imports
            exec(source)
        print("  BACmon imports successful")
    except Exception as e:
        raise ImportError(f"Failed to import in BACmon.py: {str(e)}")

def test_xml_element_functionality():
    """Test basic functionality of the XML Element class"""
    import XML
    
    # Create a simple element
    el = XML.Element('test')
    
    # Test attribute setting and getting
    el['id'] = 'test-id'
    if el['id'] != 'test-id':
        raise ValueError("Element attribute setting/getting failed")
        
    # Test content append
    el.append("test content")
    if len(el.content) != 1:
        raise ValueError("Element append failed")
        
    # Test string conversion
    str_output = str(el)
    if '<test id="test-id">test content</test>' not in str_output:
        raise ValueError(f"Element string conversion failed: {str_output}")
    
    print("  XML Element functionality works correctly")

def test_dictionary_methods():
    """Test dictionary methods for Python 3 compatibility"""
    test_dict = {'a': 1, 'b': 2, 'c': 3}
    
    # Test keys() returns a view, not a list
    keys = test_dict.keys()
    if not hasattr(keys, '__iter__'):
        raise ValueError("keys() should return an iterable view in Python 3")
    
    # Test items() returns a view, not a list
    items = test_dict.items()
    if not hasattr(items, '__iter__'):
        raise ValueError("items() should return an iterable view in Python 3")
    
    # Test values() returns a view, not a list
    values = test_dict.values()
    if not hasattr(values, '__iter__'):
        raise ValueError("values() should return an iterable view in Python 3")
    
    # Test 'in' operator instead of has_key()
    if 'a' not in test_dict:
        raise ValueError("'in' operator not working as expected")
    
    print("  Dictionary methods work correctly in Python 3")

def test_xhtml_module():
    """Test basic XHTML module functionality"""
    import XHTML
    
    # Create a simple document
    doc = XHTML.Document()
    
    # Add a paragraph
    doc.append(XHTML.P("Test paragraph"))
    
    # Convert to string
    str_output = str(doc)
    
    # Check if output contains expected elements
    if "<!DOCTYPE" not in str_output:
        raise ValueError("XHTML doctype missing")
    if "<html" not in str_output:
        raise ValueError("XHTML html element missing")
    if "<p>Test paragraph</p>" not in str_output:
        raise ValueError("XHTML paragraph not rendered correctly")
    
    print("  XHTML module functionality works correctly")

def test_map_functions():
    """Test that map functions return proper iterators in Python 3"""
    # Create a test list
    test_list = [1, 2, 3, 4, 5]
    
    # Test map function
    mapped = map(lambda x: x * 2, test_list)
    
    # In Python 3, map returns an iterator, not a list
    if isinstance(mapped, list):
        raise ValueError("map() should return an iterator, not a list in Python 3")
    
    # Convert to list and verify the values
    mapped_list = list(mapped)
    if mapped_list != [2, 4, 6, 8, 10]:
        raise ValueError(f"map() function not working correctly, got {mapped_list}")
    
    print("  map() function works correctly in Python 3")

def test_division():
    """Test that division works as expected in Python 3"""
    # Test that normal division produces float results
    result = 5 / 2
    if result != 2.5:
        raise ValueError(f"Division should produce float results, got {result}")
    
    # Test that floor division produces integer results
    result = 5 // 2
    if result != 2:
        raise ValueError(f"Floor division should produce integer results, got {result}")
    
    print("  Division operators work correctly in Python 3")

def test_print_function():
    """Test that print works as a function in Python 3"""
    try:
        # This should work in Python 3
        print("Testing print function")
        
        # This would have worked in Python 2 but not in Python 3
        try:
            eval('print "This should fail in Python 3"')
            raise ValueError("Python 2 print statement syntax should not work in Python 3")
        except SyntaxError:
            # This is expected in Python 3
            pass
        
        print("  print() function works correctly in Python 3")
    except Exception as e:
        raise RuntimeError(f"Print function test failed: {str(e)}")

def test_timeutil():
    """Test functionality in timeutil.py"""
    import timeutil
    
    # Test basic functionality
    try:
        # Test creating an AbsoluteTime
        now = timeutil.AbsoluteTime()
        
        # Test string representation
        str_rep = str(now)
        print(f"  timeutil.AbsoluteTime created: {str_rep}")
        
        # Test DeltaTime
        delta = timeutil.DeltaTime(hours=1)
        str_rep = str(delta)
        print(f"  timeutil.DeltaTime created: {str_rep}")
        
    except Exception as e:
        raise RuntimeError(f"timeutil test failed: {str(e)}")

def summarize_results():
    """Print a summary of test results"""
    total = len(test_results["passed"]) + len(test_results["failed"])
    
    print("\n==== TEST SUMMARY ====")
    print(f"Total tests: {total}")
    print(f"Passed: {len(test_results['passed'])}")
    print(f"Failed: {len(test_results['failed'])}")
    
    if test_results["failed"]:
        print("\nFailed tests:")
        for test in test_results["failed"]:
            print(f"  - {test}")
        return False
    else:
        print("\nAll tests passed! 🎉")
        return True

def main():
    """Run all tests"""
    print("Starting Python 3 compatibility tests...\n")
    
    # Run all tests
    run_test("Module Imports", test_import_modules)
    run_test("BACmon Imports", test_bacmon_imports)
    run_test("XML Element Functionality", test_xml_element_functionality)
    run_test("Dictionary Methods", test_dictionary_methods)
    run_test("XHTML Module", test_xhtml_module)
    run_test("Map Functions", test_map_functions)
    run_test("Division Operators", test_division)
    run_test("Print Function", test_print_function)
    run_test("Timeutil Module", test_timeutil)
    
    # Summarize results
    success = summarize_results()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 