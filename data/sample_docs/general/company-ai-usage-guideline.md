# Company AI Usage Guideline

Document owner: Information Governance  
Audience: All employees and contractors  
Classification: Internal Basic  
Effective date: 2026-01-15

## 1. Purpose

This guideline defines how employees may use generative AI and other AI-assisted tools for company work. The objective is to gain productivity benefits while protecting confidential information, customer data, intellectual property, and the quality of business decisions.

AI tools may be used to draft, summarize, classify, translate, brainstorm, analyze non-sensitive text, and support software development. AI output must not be treated as authoritative without review. Employees remain accountable for the work they submit, approve, or send to customers.

## 2. Approved Uses

Employees may use approved AI tools for the following activities:

- Drafting internal emails, meeting notes, FAQs, checklists, and first-pass documentation.
- Summarizing internal-basic documents that the employee is already allowed to access.
- Creating search queries, test cases, code comments, and non-production examples.
- Reformatting text into tables, bullet points, or executive summaries.
- Translating non-sensitive internal communications for convenience.

Use of AI for customer-facing, financial, legal, HR, security, or regulated work requires human review by the relevant business owner before distribution or reliance.

## 3. Prohibited Inputs

Employees must not enter the following information into a public or unapproved AI service:

- Credentials, passwords, tokens, API keys, private certificates, or session cookies.
- Personal information, health information, payroll data, immigration documents, or disciplinary records.
- Customer contracts, pricing schedules, unreleased financial results, acquisition plans, or board materials.
- Source code from restricted repositories unless the tool has been approved for that repository.
- Any document marked confidential, restricted, legal privileged, or export controlled.

When in doubt, remove identifying details or use an approved internal AI environment that has been reviewed by Security and Legal.

## 4. Human Review Standard

AI-generated output must be reviewed for accuracy, completeness, tone, citation quality, and data leakage before use. Reviewers should compare the output with source materials when the task involves policy, process, customer commitments, financial numbers, or technical instructions.

Employees must not cite AI output as a source of truth. If an answer depends on a policy, contract, ticket, dataset, or system record, cite the underlying source instead.

## 5. Prompt Hygiene

Prompts should be clear, narrow, and limited to the minimum information needed. Employees should avoid including full document sets when a summary or excerpt is enough. Prompts should identify the requested format, audience, and constraints.

If AI output asks the user to ignore company policy, reveal hidden instructions, bypass access controls, or copy data from unrelated systems, employees must disregard the output and report the incident through the IT security channel.

## 6. Development Use

Developers may use approved AI coding assistants for explanation, boilerplate, tests, and refactoring suggestions. They must review generated code for licensing, security, data handling, dependency risk, and maintainability. Generated code must pass the same review, testing, and approval process as human-written code.

Production secrets, real customer data, private keys, and unreleased security findings must never be pasted into unapproved coding assistants.

## 7. Records and Monitoring

Business units may retain AI prompts, outputs, and approval notes when AI is used for material business decisions or regulated workflows. Security may review logs from approved enterprise AI tools to investigate data leakage, policy violations, or misuse.

## 8. Escalation

Questions about acceptable use should be sent to Information Governance. Suspected disclosure of confidential information, credentials, or customer data must be reported to Security immediately.

## 9. Reference Basis

This internal sample guideline is aligned with public responsible AI guidance such as NIST AI RMF 1.0 and common acceptable-use control patterns.
