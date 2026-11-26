# Senior Backend Developer – Practical Hiring Assignment
## Pishtaz Teb Zaman Company | Project: Employee Supplementary Health Insurance Renewal System

- **Time Limit:** Maximum 8 hours
- **Primary Technologies:** Python and Django
- **Level:** Senior

---

## 1. Project Objective

Design and implement an initial version of a web-based system for managing the annual renewal of supplementary health insurance for employees and their dependents.

**Note:** The objective is not to build a complete insurance product, but rather to evaluate the candidate's ability to analyze a problem, model data, implement a usable workflow, and produce maintainable code.

## 2. Scenario Description

The company has a number of employees. At the beginning of each annual renewal period, information about individuals covered during the previous year is already available in the system.

An employee logs into the system, reviews their own information and that of their dependents, and submits a coverage request for the new period.

The employee can:
- Add a new dependent.
- Choose not to include a previously covered dependent in the new period.
- Modify an individual's information.

The employee then submits the request to the Human Resources department.

The HR representative can either give the request final approval or return it for correction, providing a reason.

The employee can view the request status and its review history.

## 3. Business Rules

- Each employee can have only one request per renewal period.
- An employee can request coverage for themselves and a number of dependents (spouse, children, or parents). Document verification and legal eligibility assessment for dependents are outside the scope of this assignment.
- A request can be created and edited while in Draft status.
- After submission, the request cannot be edited unless it is returned for correction.
- HR can only give final approval to submitted requests or return them for correction with a specified reason.
- When a request is in the Requires Correction status, the employee can edit the information and resubmit it.
- A finally approved request cannot be edited.
- The history of submissions, returns, and approvals must be recorded along with the timestamp, person performing the action, and explanation.
- Employees can only access their own requests; authorized HR users can review all requests.
- Records from previous renewal periods must remain accessible even after information is modified in a new period.

## 4. Required Information

| Entity | Minimum Required Information |
|---|---|
| Employee | Employee ID, first and last name, organizational unit |
| Insured Individual | First and last name, national ID (string), relationship: self/spouse/child, date of birth |
| Renewal Period | Period title, coverage start date and end date |
| Request | Employee, period, status, selected individuals, creation/submission timestamps, decision history |

Designing the database table structure, relationships, and database rules is your responsibility. Use mock data.

## 5. Mandatory Features

### A. Employee Panel

- Log into the system, view existing data, create requests, and manage selected individuals.
- Save drafts, submit requests, view their status, edit returned requests, and resubmit them.

### B. Human Resources Panel

- View and filter requests by renewal period and status.
- View request details and either approve or return requests for correction with a reason.

### C. Basic Reporting

- Number of requests broken down by status for a selected renewal period.
- Number of individuals selected for coverage in approved requests.

### D. Integrity and Security

- Prevent duplicate requests for the same employee within a renewal period.
- Enforce permissions and valid status transitions on the server side; validate inputs.

### E. User Interface

- Simple, understandable, and usable web forms and pages without relying on Django Admin.
- Display validation errors and operation statuses to the user.

## 6. Technical Scope and Constraints

- Python and Django are mandatory; SQLite is sufficient for this project.
- Using Django Templates, HTML/CSS, and Bootstrap is permitted; a separate frontend is not required.
- Use Django's built-in authentication system; dependents do not need separate accounts.
- Django Admin is permitted only for creating or inspecting test data, not as a replacement for the workflow interfaces.
- The use of AI is permitted; however, the candidate is responsible for the correctness of and understanding the submitted code.
- Integration with SQL Server, Excel, PDF, SMS, Docker, standalone APIs, and insurance premium calculation is not required.
- The application must be possible to run and deploy without external services.

## 7. Acceptance Scenarios

| # | Testable Scenario |
|---|---|
| 1 | An employee creates a request, adds their spouse, and submits it; HR approves the request. |
| 2 | HR returns a request with a reason; the employee makes corrections and resubmits it. |
| 3 | An employee attempts to view or modify another employee's information by changing the request ID/URL; access is denied. |
| 4 | An employee attempts to create a second request within the same renewal period; the system prevents it. |
| 5 | Changes to information in a new renewal period do not corrupt the records of requests from previous periods. |

## 8. Deliverables

- A Git repository containing the complete source code and database migrations.
- Clear instructions for creating test users with Employee and HR roles, and creating at least two renewal periods.
- Several meaningful automated tests covering the main workflow, unauthorized access, and important business rules.
- A README containing prerequisites, installation instructions, migration execution, test execution, assumptions, and limitations.
- A list of unfinished items (if any) and the actual time spent.

## 9. Evaluation Criteria and Technical Review Session

The evaluation will focus on understanding the workflow, data design, Django code quality, security, workflow correctness, testability, user interface, and ability to run the application.

The number of additional features implemented does not independently contribute to the evaluation score.

If time is limited, complete the main workflow and explain any unfinished items.

After submission, an approximately 45-minute technical review session will be held to demonstrate the application and explain design decisions.

A small change to the requirements may also be introduced during this session.

---

**Good luck!**