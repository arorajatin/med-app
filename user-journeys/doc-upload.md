# Report Upload and Automatic Assignment Journey

## Goal

Capture one medical report through the authenticated V1 web app, store it privately, and categorize it under the existing family profile identified in the document.

## Authenticated web upload

1. The account manager signs in to the V1 web app and opens Upload.
2. The account manager selects an existing family profile as provisional context.
3. The account manager chooses one input:
   - capture pages with the camera;
   - select one image;
   - select one PDF;
   - select multiple images representing one report.
4. For camera or multiple-image input, the account manager previews, reorders, removes, or retakes pages before submission.
5. All selected pages are treated as one logical report.
6. The account manager may enter optional descriptive context, which is stored separately and never used as source evidence for a condition or diagnosis.
7. The browser sends the logical report to an authenticated upload endpoint; it does not write directly to Supabase Storage or choose an internal storage path.
8. The service verifies the account and selected profile, validates the content and product limits, and stamps immutable `direct_file` or `camera` provenance.
9. The service privately stores every validated source part, and the web app displays upload progress using safe report metadata.
10. The report becomes upload complete only after every part is durable.
11. The completed upload becomes eligible for Feed.
12. One logical-document extraction begins in the background under the account-level AI consent accepted during onboarding, without another consent prompt.

Direct-to-storage client uploads are prohibited; authenticated API-mediated web uploads are the supported V1 upload path. Email, inbound aliases, external connectors, and other non-web ingestion paths are outside V1.

## Patient detection and assignment

1. Extraction identifies patient-name evidence from the report or prescription and may retain a source-linked date of birth when the document contains one. The date of birth is not copied to a profile or used for matching.
2. Matching considers only profiles and aliases owned by the account.
3. Exactly one normalized full-name or explicit-alias match becomes the report's selected profile, even when it differs from the provisional selection.
4. The app shows when extracted patient evidence changed the assignment.
5. When zero or multiple profiles match exactly, or only partial/fuzzy similarity exists, the report becomes `Needs assignment`. The provisional selection alone never resolves the report.
6. The account manager resolves the item to an existing profile.
7. The system never creates a family profile solely from extracted output.
8. Metrics and candidate memory do not publish until assignment resolves.

## Condition-extraction boundary

1. A prescription or lab report may produce a pending `documented_condition_candidate` only when the document literally contains text that names the condition.
2. The candidate retains the exact written condition text and the exact source reference that supports it.
3. Medication or dosage details, lab values or ranges, abnormal flags, symptoms, optional upload context, and general medical knowledge never create a condition candidate.
4. Only an account-manager decision of `confirm` or `edit` allows the condition to enter trusted downstream memory; `ignore` keeps it out.

## Generated display name

The original source filename is always retained. The system may propose a clearer display filename as a review-required metadata candidate. An explicit user rename takes precedence.

## Alternate and failure paths

- Unsupported, empty, corrupt, inaccessible encrypted, or oversized content fails with an actionable message.
- A partial multi-image upload never appears as completed.
- A failed upload retains no misleading completed report.
- Extraction failure does not undo a completed private upload; Feed shows the processing failure and a valid retry action.
- Multiple independent reports in one direct-upload batch are outside the first release.
- Email or connector intake is not offered as an alternate V1 upload path.
