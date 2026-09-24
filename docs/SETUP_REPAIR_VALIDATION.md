# Setup repair verification

22 backend tests passed. React production build passed.
Automated Chromium browser checks passed: username validation; wrong setup code error; administrator creation using SETUP_CODE.txt; dashboard; logout; login; session after refresh.
Tests used a temporary database. No test accounts or databases are included.
Windows batch launcher was reviewed but not executed on Windows in this environment.

The setup code is randomly generated each time the server starts. The former chat instructions suggesting 1929 were incorrect. The name supports spaces. Usernames allow letters, digits, dots, underscores and dashes, but not email addresses.

All existing incident, team, monitoring, export and optional local AI features remain included.
