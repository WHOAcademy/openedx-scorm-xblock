/**
 * Unit tests for isAdaptLearningToolStatusCompleted(scormData, scormWindow).
 *
 * Ported from scorm_v2's test_scormxblock.js (commit e5a2556), rewritten against
 * the current two-argument signature. The v2 tests called the function with a
 * single argument and relied on a document.getElementById("scorm-iframe-175525")
 * mock; the current function takes the SCORM window directly as its second
 * argument instead of looking up a hard-coded iframe id internally, so every
 * test case below constructs and passes a mock window explicitly rather than
 * mocking document.getElementById. Every "should return true" case genuinely
 * exercises SCORMSuspendData.deserialize() through the mock, rather than
 * accidentally passing because of an unrelated thrown exception.
 *
 * Run this in a browser console or include in a test runner (test_runner.html).
 */

// A working mock of SCORMSuspendData.deserialize, mirroring the real
// Adapt Learning encoding: index 0 of the result is the completion flag.
// https://github.com/adaptlearning/adapt-contrib-spoor?tab=readme-ov-file#print-completion-information-from-lms-data
function makeMockScormWindow() {
    return {
        SCORMSuspendData: {
            deserialize: function (status) {
                switch (status) {
                    case "hIA": return [true, false];   // Completed, Not Passed
                    case "hAA": return [false, false];  // Not Completed, Not Passed
                    case "hMA": return [true, true];     // Completed, Passed
                    default: return [false, false];
                }
            }
        }
    };
}

// A mock window whose SCORMSuspendData.deserialize always throws, to exercise
// the try/catch around the deserialize call itself (distinct from the case
// where scormWindow is missing entirely).
function makeThrowingMockScormWindow() {
    return {
        SCORMSuspendData: {
            deserialize: function () {
                throw new Error("corrupted suspend_data payload");
            }
        }
    };
}

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

    // ---- Guard-clause cases: these must return false before scormWindow is
    // ever touched, so a mock window that would throw on any access is used
    // deliberately -- if any of these secretly reached the deserialize call,
    // the test would fail with "corrupted suspend_data payload" instead of
    // the expected assertion error, making a signature/guard regression obvious.
    const poisonedWindow = makeThrowingMockScormWindow();

    test('should return false when scorm_data is null', function () {
        const result = isAdaptLearningToolStatusCompleted(null, poisonedWindow);
        assertFalse(result, 'Should return false for null scorm_data');
    });

    test('should return false when scorm_data is undefined', function () {
        const result = isAdaptLearningToolStatusCompleted(undefined, poisonedWindow);
        assertFalse(result, 'Should return false for undefined scorm_data');
    });

    test('should return false when cmi.suspend_data is missing', function () {
        const scorm_data = { 'cmi.core.lesson_status': 'completed' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when cmi.suspend_data is missing');
    });

    test('should return false when cmi.suspend_data is null', function () {
        const scorm_data = { 'cmi.suspend_data': null };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when cmi.suspend_data is null');
    });

    test('should return false when cmi.suspend_data is empty string', function () {
        const scorm_data = { 'cmi.suspend_data': '' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when cmi.suspend_data is empty string');
    });

    test('should return false when suspend_data is invalid JSON string', function () {
        const scorm_data = { 'cmi.suspend_data': 'invalid json' };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false for invalid JSON string');
    });

    test('should return false when suspend_data object has no "c" property', function () {
        const scorm_data = { 'cmi.suspend_data': { 'other': 'value' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when suspend_data has no "c" property');
    });

    test('should return false when suspend_data.c is not a string (number)', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 123 } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when suspend_data.c is not a string');
    });

    test('should handle empty object suspend_data', function () {
        const scorm_data = { 'cmi.suspend_data': {} };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false for empty object suspend_data');
    });

    test('should handle suspend_data with null "c" property', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': null } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when suspend_data.c is null');
    });

    test('should handle suspend_data with undefined "c" property', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': undefined } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when suspend_data.c is undefined');
    });

    // ---- Cases that reach SCORMSuspendData.deserialize() and depend on its
    // result -- these use the real working mock, so a true/false regression in
    // the deserialize-result check (parsedSuspendData[0] === true) is caught.
    const workingWindow = makeMockScormWindow();

    test('should handle complex JSON string suspend_data', function () {
        const scorm_data = {
            'cmi.suspend_data': '{"a11y":false,"lang":"en","a":{"Head-tilt and chin-lift":"hSeAIIAAosLiBcgLmBdALqCwAAAE"},"c":"hIA","q":"jw4XEDAcAbhgDhcSMBwBgGAOFyAwHAG4YA4XUDccL4CA-cogoBocL4CA-YowYog4XwEB8xRgxRBwvgID5SjBiiDhfAQHzFGDFEHC-AgPmKMGKEOF8BAfMUYMUEA"}'
        };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, workingWindow);
        assertTrue(result, 'Should return true for complex JSON string with hIA status');
    });

    test('should return true when suspend_data.c is hIA (completed, not passed)', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hIA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, workingWindow);
        assertTrue(result, 'Should return true when suspend_data.c is hIA');
    });

    test('should return true when suspend_data.c is hMA (completed and passed)', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hMA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, workingWindow);
        assertTrue(result, 'Should return true when suspend_data.c is hMA');
    });

    test('should return false when suspend_data.c is hAA (not completed)', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hAA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, workingWindow);
        assertFalse(result, 'Should return false when suspend_data.c is hAA');
    });

    test('should return false for an unrecognized status code', function () {
        // deserialize()'s mock falls back to [false, false] for anything it
        // doesn't recognize, same as the real library would for a status it
        // can't decode -- makes sure we don't accidentally treat "truthy
        // string" alone as completion.
        const scorm_data = { 'cmi.suspend_data': { 'c': 'zzNotARealCode' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, workingWindow);
        assertFalse(result, 'Should return false for an unrecognized status code');
    });

    // ---- Cases specific to the two-argument signature itself: these did not
    // exist in v2's suite (its function had no scormWindow parameter), but
    // they cover exactly how GetValue() in scormxblock.js actually calls this
    // function -- `iframe && iframe.contentWindow` can legitimately be
    // undefined before the SCORM iframe has loaded.
    test('should return false when scormWindow is undefined, even with a valid "c"', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hIA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, undefined);
        assertFalse(result, 'Should return false when scormWindow is undefined');
    });

    test('should return false when scormWindow has no SCORMSuspendData', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hIA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, {});
        assertFalse(result, 'Should return false when scormWindow.SCORMSuspendData is missing');
    });

    test('should return false when SCORMSuspendData.deserialize throws', function () {
        const scorm_data = { 'cmi.suspend_data': { 'c': 'hIA' } };
        const result = isAdaptLearningToolStatusCompleted(scorm_data, poisonedWindow);
        assertFalse(result, 'Should return false when deserialize() throws');
    });

    // Run all tests
    console.log('Running isAdaptLearningToolStatusCompleted tests...\n');

    tests.forEach(function (testCase) {
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
