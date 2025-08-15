function ScormXBlock(settings) {
  
  function SCORM_12_API() {
    this.LMSInitialize = function () {
      return "true";
    };

    this.LMSFinish = function () {
      return "true";
    };

    this.LMSGetValue = GetValue;
    this.LMSSetValue = SetValue;

    this.LMSCommit = function () {
      return "true";
    };

    this.LMSGetLastError = function () {
      return "0";
    };

    this.LMSGetErrorString = function (errorCode) {
      return "Some Error";
    };

    this.LMSGetDiagnostic = function (errorCode) {
      return "Some Diagnostic";
    };
  }

  function SCORM_2004_API() {
    this.Initialize = function () {
      return "true";
    };

    this.Terminate = function () {
      return "true";
    };

    this.GetValue = GetValue;
    this.SetValue = SetValue;

    this.Commit = function () {
      return "true";
    };

    this.GetLastError = function () {
      return "0";
    };

    this.GetErrorString = function (errorCode) {
      return "Some Error";
    };

    this.GetDiagnostic = function (errorCode) {
      return "Some Diagnostic";
    };
  }


  var GetValue = function (cmi_element) {
    // console.log("%cSERVER: GetValue: " + cmi_element, "color: blue");
    if(cmi_element == "cmi.completion_status") {
      return "completed";
    }
    return "";
  };

  var SetValue = function (cmi_element, value) {
    if(cmi_element == "cmi.completion_status") {
      console.log("%cSERVER: SetValue: " + cmi_element + " " + value, "color: red");
    }
    return "true";
  };

  // Added to fix MCM Score issue
  // TODO::Implement rest of the LMS API
  // http://rustici-docs.s3.amazonaws.com/driver/Function-List.html#scoring
  var SetScore = function (intScore, intMaxScore, intMinScore) {
    // SCORM 1.2 - cmi.core.score.raw
    // SCORM 2004 - cmi.score.raw
    if (settings.scorm_version == "SCORM_12") {
      SetValue("cmi.core.score.raw", intScore);
    } else {
      SetValue("cmi.score.raw", intScore);
    }
  };
  var GetScore = function () {
    // SCORM 1.2 - cmi.core.score.raw
    // SCORM 2004 - cmi.score.raw
    if (settings.scorm_version == "SCORM_12") {
      return GetValue("cmi.core.score.raw");
    } else {
      return GetValue("cmi.score.raw");
    }
  };
  var CommitData = function () {
    return true;
  };

  
  // https://scorm.com/scorm-explained/technical-scorm/run-time/
  if (settings.scorm_version == "SCORM_12") {
    window.API = new SCORM_12_API();
  } else {
    window.API_1484_11 = new SCORM_2004_API();
  }

  // Added to fix MCM Score issue
  // TODO::Implement rest of the LMS API
  // http://rustici-docs.s3.amazonaws.com/driver/Function-List.html#scoring
  window.lmsAPI = {
    SetScore: SetScore,
    GetScore: GetScore,
    CommitData: CommitData,
  };

}

// scorm_version: SCORM_12 or SCORM_2004
ScormXBlock({scorm_version: "SCORM_2004"});
