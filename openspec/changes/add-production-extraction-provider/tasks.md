## 1. Provider Evaluation

- [ ] 1.1 Define supported document formats and a de-identified evaluation fixture set.
- [ ] 1.2 Compare providers on privacy, retention, region, accuracy, source context, latency, and cost.
- [ ] 1.3 Record the selected provider, rejected alternatives, and rollout thresholds in the design.

## 2. Adapter Implementation

- [ ] 2.1 Add validated provider configuration and secret handling with production fail-closed behavior.
- [ ] 2.2 Implement the provider adapter behind the normalized extractor contract.
- [ ] 2.3 Normalize document type, fields, confidence, and source references.
- [ ] 2.4 Make extraction attempts atomic across raw output, fields, and statuses.
- [ ] 2.5 Add redacted metrics and safe failure classification.

## 3. Verification and Rollout

- [ ] 3.1 Add provider contract, normalization, unsupported-file, timeout, and partial-failure tests.
- [ ] 3.2 Compare extraction output with the approved fixture thresholds.
- [ ] 3.3 Verify pending review and consent behavior remain unchanged end to end.
- [ ] 3.4 Document staging rollout, production enablement, cost controls, and rollback.
- [ ] 3.5 Run the backend test suite and strict OpenSpec validation.
- [ ] 3.6 Complete implementation review and finalize `review.md` with the reviewed commit, test evidence, findings, and resume state.
