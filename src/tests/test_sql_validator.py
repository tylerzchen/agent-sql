import csv
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sql_agent import SQLAgent

def load_test_cases(csv_file_path: str):
    test_cases = []
    csv_path = os.path.join(current_dir, csv_file_path)
    with open(csv_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            test_cases.append({
                'query': row['query'],
                'expected_valid': row['expected_valid'].lower() == 'true',
                'note': row.get('note', '')
            })
        return test_cases

def test_sql_validator():
    print("Testing SQL validator...")
    sql_agent = SQLAgent()
    test_cases = load_test_cases('sql_validation_tests.csv')
    
    results = {
        'total_tests': len(test_cases),
        'passed': 0,
        'failed': 0,
        'false_positives': 0,
        'false_negatives': 0,
        'failures': []
    }

    for i, test_case in enumerate(test_cases, 1):
        print(f"Testing {i}/{len(test_cases)}: {test_case['query'][:50]}...")
        is_valid, error = sql_agent.validate_sql(test_case['query'])

        if is_valid == test_case['expected_valid']:
            results['passed'] += 1
        else:
            results['failed'] += 1
            if test_case['expected_valid'] and not is_valid:
                results['false_positives'] += 1
                failure_type = "False Positive"
            else:
                results['false_negatives'] += 1
                failure_type = "False Negative"
            
            results['failures'].append({
                'query': test_case['query'],
                'expected': test_case['expected_valid'],
                'actual': is_valid,
                'error': error,
                'failure_type': failure_type,
                'notes': test_case['note']
            })

    print(f"\n=== VALIDATION TEST RESULTS ===")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"False Positives: {results['false_positives']}")
    print(f"False Negatives: {results['false_negatives']}")
    
    if results['failures']:
        print(f"\n=== FAILURES ===")
        for failure in results['failures']:
            print(f"\n{failure['failure_type']}: {failure['query']}")
            print(f"Expected: {failure['expected']}, Got: {failure['actual']}")
            print(f"Error: {failure['error']}")
            print(f"Notes: {failure['notes']}")
    
    return results

if __name__ == "__main__":
    test_sql_validator()