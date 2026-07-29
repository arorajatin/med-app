# Profile and Family Management Journey

## Goal

Let one account manager maintain `self` and the family profiles whose reports they manage.

## Journey

1. The account manager opens Profile.
2. The screen shows account email and image plus `self` and every owned family profile.
3. Opening a family profile shows its relationship, reported age and weight, reviewed major conditions, and current reviewed medications.
4. The account manager can add another family member with at least a display name and relationship.
5. Optional starting context includes age, unit-aware weight, current conditions, and current medications.
6. Conditions and medications entered directly by the account manager become trusted user-attested memory.
7. The profile becomes available in Chat, Upload, and Drive selectors.
8. No family profile receives credentials or an independent session.

## Family presentation

The first release presents an owner-relative family list or tree. It does not model every relationship between every pair of family members.

## Error and access behavior

- Invalid profile health context is rejected without discarding valid saved context.
- Missing and foreign profiles behave as unavailable.
- A profile cannot be created automatically solely because AI extracted an unfamiliar patient name.

