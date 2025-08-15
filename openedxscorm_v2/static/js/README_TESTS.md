# Unit Tests for isAdaptLearningToolStatusCompleted

This directory contains comprehensive unit tests for the `isAdaptLearningToolStatusCompleted` method in the ScormXBlock.

## Files

- `test_scormxblock.js` - The main test file containing all test cases
- `test_runner.html` - HTML test runner for easy browser-based testing
- `README_TESTS.md` - This documentation file
## How to Run Tests

### Option 1: Browser Test Runner (Recommended)

1. Open `test_runner.html` in a web browser
2. Click the "Run Tests" button
3. View the results in the console output area

### Option 2: Browser Console

1. Open the browser console
2. Load the original `scormxblock.js` file
3. Load the `test_scormxblock.js` file
4. Run `runTests()` in the console

### Option 3: Node.js (if available)

```bash
# If you have Node.js and a test runner like Jest
npm install --save-dev jest
jest test_scormxblock.js
```

## Test Results

The tests will output:
- Individual test results with ✓ (pass) or ✗ (fail)
- Summary of passed/failed tests
- Total test count

Example output:
```
Running isAdaptLearningToolStatusCompleted tests...

✓ should return false when scorm_data is null
✓ should return false when scorm_data is undefined
...

Test Results:
Passed: 15
Failed: 0
Total: 15
```

## Mock Dependencies

The tests include mocks for:
- `window.SCORMSuspendData.deserialize()` - Returns completion status based on Adapt status codes
- `document.getElementById()` - Returns mock iframe with SCORMSuspendData

## Adding New Tests

To add new test cases:

1. Add a new test function in `test_scormxblock.js`:
```javascript
test('should handle new scenario', function() {
    const scorm_data = { /* test data */ };
    const result = isAdaptLearningToolStatusCompleted(scorm_data);
    assertTrue(result, 'Expected behavior description');
});
```

2. Run the tests to ensure they pass

## Status Code Reference

Based on the Adapt Learning serializion algorithm:
- `hIA` = [true, false] - Completed but Not Passed
- `hAA` = [false, false] - Not Completed and Not Passed
- `hMA` = [true, true] - Completed and Passed

The `isAdaptLearningToolStatusCompleted` method only checks the first element (completion status) and returns `true` if it's `true`.
