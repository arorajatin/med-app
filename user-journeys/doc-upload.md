# Report Upload and Automatic Assignment Journey

## Goal

Capture one medical report, store it privately, and categorize it under the existing family profile identified in the document.

## Direct upload

1. The account manager opens Upload.
2. The account manager selects an existing family profile as provisional context.
3. The account manager chooses one input:
   - capture pages with the camera;
   - select one image;
   - select one PDF;
   - select multiple images representing one report.
4. For camera or multiple-image input, the account manager previews, reorders, removes, or retakes pages before submission.
5. All selected pages are treated as one logical report.
6. The account manager may enter optional descriptive context.
7. The client displays upload progress.
8. The service privately stores every source part and required metadata.
9. The report becomes upload complete only after every part is durable.
10. The completed upload becomes eligible for Feed.
11. If account-level AI consent is accepted, one logical-document extraction begins in the background.

## Patient detection and assignment

1. Extraction identifies patient-name evidence from the report or prescription.
2. Matching considers only profiles and aliases owned by the account.
3. A single confident existing-profile match becomes the report's selected profile, even when it differs from the provisional selection.
4. The app shows when extracted patient evidence changed the assignment.
5. When no existing profile matches confidently or multiple profiles are plausible, the report becomes `Needs assignment`.
6. The account manager resolves the item to an existing profile.
7. The system never creates a family profile solely from extracted output.
8. Metrics and candidate memory do not publish until assignment resolves.

## No-AI path

If account-level AI processing was not accepted, a direct upload uses the account manager's provisional selection as the resolved profile and does not start extraction. An external import without a preselection requires manual assignment.

## Generated display name

The original source filename is always retained. The system may propose a clearer display filename from trusted report metadata. An explicit user rename takes precedence.

## Alternate and failure paths

- Unsupported, empty, corrupt, inaccessible encrypted, or oversized content fails with an actionable message.
- A partial multi-image upload never appears as completed.
- A failed upload retains no misleading completed report.
- Extraction failure does not undo a completed private upload; Feed shows the processing failure and a valid retry action.
- Multiple independent reports in one direct-upload batch are outside the first release.

