/**
 * Unit tests for isAdaptLearningToolStatusCompleted method
 * Run this in a browser console or include in a test runner
 */

// Mock SCORMSuspendData for testing
window.SCORMSuspendData = {
    deserialize: function(status) {
        // Mock implementation based on the status codes
        switch(status) {
            case 'hIA': return [true, false];   // Completed, Not Passed
            case 'hAA': return [false, false];  // Not Completed, Not Passed  
            case 'hMA': return [true, true];    // Completed, Passed
            default: return [false, false];
        }
    }
};

// Mock document.getElementById for iframe
const originalGetElementById = document.getElementById;
document.getElementById = function(id) {
    if (id === 'scorm-iframe') {
        return {
            contentWindow: {
                SCORMSuspendData: window.SCORMSuspendData
            }
        };
    }
    return originalGetElementById.apply(document, arguments);
};

// Test framework
function runTests() {
    let passed = 0;
    let failed = 0;
    const tests = [];

    function test(name, testFn) {
        tests.push({ name, testFn });
    }

    function assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(`${message || 'Assertion failed'}: expected ${expected}, got ${actual}`);
        }
    }

    function assertTrue(actual, message) {
        assertEqual(actual, true, message);
    }

    function assertFalse(actual, message) {
        assertEqual(actual, false, message);
    }

    // Test cases for isAdaptLearningToolStatusCompleted
    test('should return false when scorm_data is null', function() {
        const result = isAdaptLearningToolStatusCompleted(null);
        assertFalse(result, 'Should return false for null scorm_data');
    });

    test('should return false when scorm_data is undefined', function() {
        const result = isAdaptLearningToolStatusCompleted(undefined);
        assertFalse(result, 'Should return false for undefined scorm_data');
    });

    test('should return false when cmi.suspend_data is missing', function() {
        const scorm_data = { 'cmi.core.lesson_status': 'completed' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when cmi.suspend_data is missing');
    });

    test('should return false when cmi.suspend_data is null', function() {
        const scorm_data = { 'cmi.suspend_data': null };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when cmi.suspend_data is null');
    });

    test('should return false when cmi.suspend_data is empty string', function() {
        const scorm_data = { 'cmi.suspend_data': '' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when cmi.suspend_data is empty string');
    });

    test('should return false when suspend_data is invalid JSON string', function() {
        const scorm_data = { 'cmi.suspend_data': 'invalid json' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false for invalid JSON string');
    });

    test('should return false when suspend_data object has no "c" property', function() {
        const scorm_data = { 'cmi.suspend_data': { 'other': 'value' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when suspend_data has no "c" property');
    });

    test('should return false when suspend_data.c is not a string', function() {
        const scorm_data = { 'cmi.suspend_data': { 'c': 123 } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when suspend_data.c is not a string');
    });

    test('should handle complex JSON string suspend_data', function() {
        const scorm_data = { 
            'cmi.suspend_data': '{"a11y":false,"lang":"en","a":{"Head-tilt and chin-lift":"hSeAIIAAosLiBcgLmBdALqCwAAAE"},"c":"hIA","q":"jw4XEDAcAbhgDhcSMBwBgGAOFyAwHAG4YA4XUDccL4CA-cogoBocL4CA-YowYog4XwEB8xRgxRBwvgID5SjBiiDhfAQHzFGDFEHC-AgPmKMGKEOF8BAfMUYMUEA"}' 
        };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertTrue(result, 'Should return true for complex JSON string with hIA status');
    });

    test('should return true when suspend_data.c is hIA or hMA', function() {
        let scorm_data = { 'cmi.suspend_data': { 'c': 'hIA' } };
        let result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertTrue(result, 'Should return true when suspend_data.c is hIA');
        scorm_data = { 'cmi.suspend_data': { 'c': 'hMA' } };
        result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertTrue(result, 'Should return true when suspend_data.c is hMA');
    });

    test('should return false when suspend_data.c is hAA', function() {
        let scorm_data = { 'cmi.suspend_data': { 'c': 'hAA' } };
        let result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when suspend_data.c is hAA');
    });

    test('should handle empty object suspend_data', function() {
        const scorm_data = { 'cmi.suspend_data': {} };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false for empty object suspend_data');
    });

    test('should handle suspend_data with null "c" property', function() {
        const scorm_data = { 'cmi.suspend_data': { 'c': null } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when suspend_data.c is null');
    });

    test('should handle suspend_data with undefined "c" property', function() {
        const scorm_data = { 'cmi.suspend_data': { 'c': undefined } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data);
        assertFalse(result, 'Should return false when suspend_data.c is undefined');
    });

    // Run all tests
    console.log('Running isAdaptLearningToolStatusCompleted tests...\n');
    
    tests.forEach(function(testCase) {
        try {
            testCase.testFn();
            console.log('✓ ' + testCase.name);
            passed++;
        } catch (error) {
            console.log('✗ ' + testCase.name + ': ' + error.message);
            failed++;
        }
    });

    console.log('\nTest Results:');
    console.log('Passed: ' + passed);
    console.log('Failed: ' + failed);
    console.log('Total: ' + (passed + failed));

    return { passed, failed, total: passed + failed };
}

// Export for use in other test runners
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runTests };
}
