# Sign-up and Onboarding Journey

## Goal

Create the sole account-manager identity, establish `self`, and capture starting health context. Creating the account authorizes the AI processing required by the product.

## Sign-up

1. The person chooses Google or email and password.
2. Google sign-up completes through the provider and its verified email is treated as verified.
3. Email/password sign-up creates a verification-pending identity and sends an email-verification action.
4. An email/password user cannot enter protected application areas until verification succeeds.
5. A verified identity establishes an authenticated account session.
6. Creating the application account authorizes document extraction and use of reviewed personal memory in Chat; signup states this processing boundary clearly.
7. Safe recovery is available for provider cancellation, duplicate activation attempts, invalid or expired verification, and temporary identity-provider failure.

## Self onboarding

1. The system creates exactly one `self` family profile.
2. The account manager supplies:
   - name;
   - age;
   - weight with unit in pounds or kilograms;
   - current medical conditions, including an explicit none response (allow free-text input as well);
   - current medications, including an explicit none response (allow free-text input as well).
3. Age is entered as whole completed years from 0 through 130 inclusive. It retains the date on which it was reported and is never incremented silently.
4. Weight follows the validation, normalization, and storage rules in the [Profile and Family Management Journey](profile-and-family.md#error-and-access-behavior).
5. Age and weight are always shown with their reported dates.
6. Conditions and medications entered directly by the account manager become trusted user-attested memory immediately.
7. Completed onboarding lands in Feed.

## Alternate paths

- Retrying or resuming onboarding reuses the existing `self` profile.
- Fractional or out-of-range age and weight that violates the shared profile rules keep the person on the relevant step with a correction message. These are broad input-quality limits, not clinical judgements.
- Onboarding has no separate AI-processing step or AI-disabled mode.
- Post-creation AI-processing controls and account deletion are not part of the first release.

## First-release boundary

Only the account manager authenticates. `self` and other family profiles are medical contexts, not additional login identities.
