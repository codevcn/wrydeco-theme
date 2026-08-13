# Wrydeco — Email Subscriber Session Discount Auto-Apply Implementation Guide

## 1. Objective

Implement a storefront feature for Wrydeco with the following behavior:

1. A visitor successfully submits their email through the existing email/newsletter signup flow.
2. Shopify's existing automation sends the visitor an email containing the WRY discount codes.
   - **This email automation is already completed and is OUT OF SCOPE for this task.**
3. After the email signup is confirmed successful on the storefront, the current browser session is marked as eligible for WRY auto-apply.
4. While that session remains active, the storefront automatically selects and applies the **best eligible WRY discount code** based on the current cart subtotal.
5. If the cart subtotal changes, the storefront automatically changes the WRY code to the best matching tier.
6. The auto-apply entitlement must **NOT persist into a new browsing session**.
7. Returning visitors must **NOT automatically receive a WRY discount** unless they successfully submit the email signup again in that new session.

---

## 2. Important Scope

### Already completed — DO NOT rebuild

The following part already exists and must not be reimplemented:

```text
User submits email
        ↓
Shopify records the subscription
        ↓
Shopify automatically sends an email containing the discount-code list
```

Do not modify the existing email automation unless absolutely required for compatibility.

### This task is only responsible for

```text
Successful email signup event
        ↓
Unlock WRY auto-apply for the CURRENT session
        ↓
Read current cart
        ↓
Determine the best WRY discount tier
        ↓
Apply that code automatically
        ↓
Re-evaluate whenever the cart changes
```

---

## 3. Existing Discount Codes

Assume the following discount codes already exist in Shopify Admin and are configured separately.

| Cart minimum | Discount | Code |
|---:|---:|---|
| $900 | $100 OFF | `WRY100` |
| $1,900 | $200 OFF | `WRY200` |
| $2,900 | $300 OFF | `WRY300` |
| $3,900 | $400 OFF | `WRY400` |
| $4,900 | $500 OFF | `WRY500` |
| $5,900 | $600 OFF | `WRY600` |
| $6,900 | $700 OFF | `WRY700` |
| $7,900 | $800 OFF | `WRY800` |
| $8,900 | $900 OFF | `WRY900` |
| $9,900 | $1,000 OFF | `WRY1000` |

The codes are not intended to stack with one another.

Do not recreate or rename these codes as part of this storefront task unless they are found to be missing and the task owner explicitly approves it.

---

## 4. Session Eligibility

### Do NOT store the customer's raw email

The browser does not need to persist the email address.

Do not store values such as:

```text
user_email = customer@example.com
```

Instead, store only a boolean-like session flag:

```text
wry_discount_unlocked = true
```

Use `sessionStorage`, not `localStorage`.

Recommended example:

```javascript
sessionStorage.setItem('wry_discount_unlocked', 'true');
```

To check eligibility:

```javascript
const unlocked =
  sessionStorage.getItem('wry_discount_unlocked') === 'true';
```

### Why `sessionStorage`

The desired behavior is session-scoped:

```text
Visit/session A
→ successful email signup
→ WRY auto-apply unlocked
→ refresh page
→ still unlocked in the same session

End session / return later in a new session
→ no automatic WRY entitlement
→ user must successfully subscribe again to unlock auto-apply
```

Do not use `localStorage`, cookies with long expiration, Shopify customer metafields, or another persistent browser mechanism for this auto-apply entitlement.

This feature is intentionally temporary.

---

## 5. Exact Activation Point

The WRY auto-apply system must **NOT activate merely because the page loads**.

It must **NOT activate merely because the email field contains a valid-looking email**.

It must **NOT activate when the signup request is still pending**.

It must activate only after the storefront can confirm:

> The email/newsletter signup request completed successfully.

Required sequence:

```text
User enters email
        ↓
User submits form
        ↓
Signup request starts
        ↓
Wait for confirmed success
        ↓
Set:
sessionStorage.wry_discount_unlocked = true
        ↓
Immediately evaluate the CURRENT cart
        ↓
Auto-apply the best eligible WRY code
```

If the signup fails:

```text
Do NOT set the session flag
Do NOT auto-apply a WRY discount
```

If validation fails:

```text
Do NOT set the session flag
Do NOT auto-apply a WRY discount
```

---

## 6. Auto-Apply Tier Logic

Evaluate the cart's merchandise subtotal **before applying a WRY discount** and excluding shipping/taxes.

Shopify's own discount validation remains the final authority if the storefront-calculated subtotal and Shopify's discount eligibility ever disagree.

Use the following decision table:

```text
subtotal < 900
→ no WRY code

900 <= subtotal < 1900
→ WRY100

1900 <= subtotal < 2900
→ WRY200

2900 <= subtotal < 3900
→ WRY300

3900 <= subtotal < 4900
→ WRY400

4900 <= subtotal < 5900
→ WRY500

5900 <= subtotal < 6900
→ WRY600

6900 <= subtotal < 7900
→ WRY700

7900 <= subtotal < 8900
→ WRY800

8900 <= subtotal < 9900
→ WRY900

subtotal >= 9900
→ WRY1000
```

The selected code must always be the **highest-value code whose minimum purchase requirement is satisfied**.

---

## 7. Required Examples

### Example A — $5,300 cart

```text
Session unlocked = true
Cart subtotal = $5,300

Eligible tiers:
WRY100
WRY200
WRY300
WRY400
WRY500

Best code:
WRY500
```

Result:

```text
Auto-apply WRY500
```

### Example B — $8,500 cart

```text
Session unlocked = true
Cart subtotal = $8,500

Best code:
WRY800
```

Result:

```text
Auto-apply WRY800
```

### Example C — cart increases

Initial state:

```text
Cart subtotal = $5,300
Current WRY code = WRY500
```

User adds more products:

```text
Cart subtotal becomes $8,500
```

Required result:

```text
WRY500 is no longer the best tier
        ↓
Replace WRY500
        ↓
Apply WRY800
```

There must never be multiple WRY tier codes intentionally active at the same time.

### Example D — cart decreases

Initial state:

```text
Cart subtotal = $8,500
Current WRY code = WRY800
```

User removes products:

```text
Cart subtotal becomes $3,500
```

Required result:

```text
Replace WRY800
        ↓
Apply WRY300
```

### Example E — drops below minimum

Initial state:

```text
Cart subtotal = $1,200
Current WRY code = WRY100
```

User removes products:

```text
Cart subtotal becomes $850
```

Required result:

```text
Remove WRY100
Do not apply another WRY code
```

---

## 8. When the Discount Engine Must Re-Evaluate

After the session has been unlocked, recalculate the best WRY tier whenever the cart can materially change.

At minimum, handle:

- immediately after successful email signup;
- product added to cart;
- product removed from cart;
- quantity increased;
- quantity decreased;
- cart drawer opened/refreshed if the theme rebuilds cart markup;
- cart page loaded/refreshed;
- cart subtotal changed by the theme's AJAX cart flow;
- immediately before sending the user to checkout when practical.

The implementation must work with the **existing Wrydeco theme architecture**.

Before coding:

1. Inspect the current newsletter/email form implementation.
2. Identify the exact success callback/event/state.
3. Inspect how the theme currently adds, updates, and removes cart items.
4. Identify cart drawer and cart page rendering logic.
5. Reuse existing theme events/functions where possible.
6. Avoid adding duplicate global cart listeners if the theme already exposes lifecycle events.

Do not assume a generic Dawn theme implementation if Wrydeco is customized.

---

## 9. Required Core Function

Implement one central function with a responsibility equivalent to:

```text
syncWryDiscountWithCart()
```

Conceptual behavior:

```javascript
async function syncWryDiscountWithCart() {
  // 1. Check current-session unlock flag.
  // 2. If not unlocked, exit immediately.
  // 3. Read fresh cart state.
  // 4. Calculate the best WRY code from the current subtotal.
  // 5. Detect which WRY tier code, if any, is currently active.
  // 6. If current WRY code already equals the desired code, do nothing.
  // 7. If subtotal is below $900, remove the managed WRY code.
  // 8. Otherwise replace the old managed WRY code with the desired code.
  // 9. Refresh/re-render cart UI if required by the theme.
}
```

Use a single source of truth for tier mapping rather than scattered `if` statements across multiple files.

Example data structure:

```javascript
const WRY_DISCOUNT_TIERS = [
  { minimum: 9900, code: 'WRY1000' },
  { minimum: 8900, code: 'WRY900' },
  { minimum: 7900, code: 'WRY800' },
  { minimum: 6900, code: 'WRY700' },
  { minimum: 5900, code: 'WRY600' },
  { minimum: 4900, code: 'WRY500' },
  { minimum: 3900, code: 'WRY400' },
  { minimum: 2900, code: 'WRY300' },
  { minimum: 1900, code: 'WRY200' },
  { minimum: 900, code: 'WRY100' },
];
```

Use store currency-safe numeric handling.

Do not compare formatted strings such as:

```text
"$5,300.00"
```

Convert/use the cart's numeric money representation correctly.

---

## 10. Only Manage WRY Tier Codes

This feature owns only these codes:

```text
WRY100
WRY200
WRY300
WRY400
WRY500
WRY600
WRY700
WRY800
WRY900
WRY1000
```

Do not automatically remove or rewrite unrelated discount codes.

Examples of unrelated codes:

```text
WELCOME10
VIP15
BLACKFRIDAY
```

If an unrelated promotion conflicts with a WRY code because Shopify does not allow them to combine, do not silently delete the unrelated code.

The implementation should avoid destructive behavior.

The WRY tier engine's responsibility is:

> Decide which WRY code should be active.

It is not responsible for deleting arbitrary customer promotions.

---

## 11. Prevent Repeated Requests / Infinite Loops

The implementation must avoid loops such as:

```text
cart update
→ discount sync
→ cart render
→ cart update event
→ discount sync
→ cart render
→ ...
```

Requirements:

- do nothing when the desired WRY code is already active;
- debounce rapid cart-change events where appropriate;
- prevent multiple concurrent sync requests;
- always fetch/read fresh cart state before making a final decision;
- avoid applying the same code repeatedly;
- handle failed requests gracefully;
- do not block normal add-to-cart behavior.

Recommended conceptual state:

```javascript
let wryDiscountSyncInProgress = false;
let wryDiscountSyncQueued = false;
```

Exact implementation can be adapted to the existing theme architecture.

---

## 12. Behavior Before Signup

The following visitor must receive **NO automatic WRY discount**:

```text
Visitor opens Wrydeco
        ↓
Adds $5,300 of products
        ↓
Has NOT successfully submitted email
```

Expected:

```text
WRY auto-apply = OFF
No automatic WRY500
```

Even though the subtotal is eligible, the session is still locked.

---

## 13. Behavior Immediately After Signup

Example:

```text
Visitor already has $5,300 in cart
        ↓
Visitor successfully submits email
        ↓
Set wry_discount_unlocked = true
        ↓
Immediately evaluate existing cart
        ↓
Best tier = WRY500
        ↓
Apply WRY500
```

The user must not be required to add another product or refresh the page before the first auto-apply occurs.

---

## 14. Refresh Behavior

Same active session:

```text
Subscribe successfully
→ unlocked
→ refresh page
→ sessionStorage still contains flag
→ WRY auto-apply remains active
```

This is expected.

---

## 15. Returning Visitor Behavior

Required behavior:

```text
Session 1
User subscribes
→ unlocked
→ WRY auto-apply works

Session ends

Later/new browsing session
User returns
→ no current-session unlock flag
→ WRY auto-apply must NOT automatically activate
```

Do not restore entitlement from:

- persistent local storage;
- the customer's email;
- Shopify customer records;
- a long-lived cookie;
- previous WRY auto-apply state.

The user can still manually use a valid discount code received in their email if Shopify allows it.

This task only controls the **automatic application experience**.

---

## 16. Do Not Treat the Session Flag as Security

`sessionStorage` is a client-side UX flag.

It is not a secure authorization system.

Do not claim that this prevents a technically knowledgeable user from manually attempting to use a known code.

The purpose is specifically:

> Automatically apply WRY discounts only after the current browsing session has completed the email signup flow.

Actual Shopify discount validation remains Shopify's responsibility.

---

## 17. Recommended UX

When a WRY code is successfully auto-applied, the cart may display a lightweight message such as:

```text
Email Subscriber Offer
WRY500 applied — You saved $500
```

Optional next-tier message:

```text
Spend $600 more to unlock $600 OFF.
```

Only add this UI if it fits the current Wrydeco cart design and does not disrupt the luxury visual styling.

Do not redesign unrelated cart UI as part of this task.

---

## 18. Next-Tier Calculation

If implementing the optional progress message:

Example:

```text
Current subtotal = $5,300
Current tier = WRY500
Next tier minimum = $5,900

Amount remaining:
$5,900 - $5,300 = $600
```

Display:

```text
Spend $600 more to unlock $600 OFF.
```

For:

```text
subtotal >= $9,900
```

there is no next tier.

Do not display a fake higher tier.

---

## 19. Edge Cases

Handle at least the following safely.

### Empty cart

```text
subtotal = $0
→ no WRY code
```

### Exactly on threshold

```text
$900
→ WRY100

$1,900
→ WRY200

$4,900
→ WRY500

$9,900
→ WRY1000
```

### One cent below threshold

```text
$899.99
→ no WRY code

$1,899.99
→ WRY100

$4,899.99
→ WRY400

$9,899.99
→ WRY900
```

### Rapid quantity changes

Only the final/current cart state should determine the resulting code.

### Network failure

Do not break cart operations.

Log a concise development error if appropriate, but avoid noisy user-facing errors unless the existing theme has an error-notification pattern.

### Discount application rejected by Shopify

Do not enter a retry loop.

Keep the cart usable.

Shopify remains the final authority on whether a discount is actually valid.

---

## 20. Test Matrix

The implementation is not complete until all of the following are verified.

| Session unlocked? | Cart subtotal | Expected automatic result |
|---|---:|---|
| No | $5,300 | No auto discount |
| No | $10,000 | No auto discount |
| Yes | $0 | No WRY code |
| Yes | $899.99 | No WRY code |
| Yes | $900 | `WRY100` |
| Yes | $1,899.99 | `WRY100` |
| Yes | $1,900 | `WRY200` |
| Yes | $2,900 | `WRY300` |
| Yes | $3,900 | `WRY400` |
| Yes | $4,900 | `WRY500` |
| Yes | $5,300 | `WRY500` |
| Yes | $5,900 | `WRY600` |
| Yes | $6,900 | `WRY700` |
| Yes | $7,900 | `WRY800` |
| Yes | $8,500 | `WRY800` |
| Yes | $8,900 | `WRY900` |
| Yes | $9,899.99 | `WRY900` |
| Yes | $9,900 | `WRY1000` |
| Yes | $15,000 | `WRY1000` |

Also test transitions:

```text
$5,300 → $8,500
WRY500 → WRY800
```

```text
$8,500 → $3,500
WRY800 → WRY300
```

```text
$1,200 → $850
WRY100 → no WRY code
```

```text
Locked session + $5,300
→ successful email signup
→ immediately WRY500
```

```text
Unlocked session
→ refresh
→ still auto-apply enabled
```

```text
End session
→ new browsing session
→ auto-apply disabled
```

---

## 21. Implementation Safety Rules

The AI implementing this task must follow these rules:

1. Inspect the current Wrydeco theme before changing code.
2. Reuse existing newsletter success handling where possible.
3. Reuse existing AJAX cart lifecycle/events where possible.
4. Do not blindly replace theme files.
5. Make minimal, localized changes.
6. Do not break normal cart functionality.
7. Do not persist customer email in browser storage.
8. Do not use `localStorage` for the entitlement.
9. Do not auto-unlock on page load.
10. Do not auto-unlock on failed email submission.
11. Do not create duplicate cart event listeners.
12. Do not create duplicate WRY codes.
13. Do not alter unrelated discounts.
14. Do not remove unrelated discount codes automatically.
15. Do not rebuild the existing email automation.
16. Do not create an infinite cart/discount refresh loop.
17. Make the implementation idempotent where practical.
18. Keep the storefront usable if discount application fails.

---

## 22. Suggested Code Organization

Adapt names to the existing repository structure.

A clean structure could be:

```text
assets/
  wry-discount-auto-apply.js
```

Responsibilities:

```text
Session eligibility
Tier selection
Cart synchronization
WRY discount replacement
Cart event integration
Optional discount-status UI
```

If the theme already has a main cart JavaScript module, integrate into it instead of creating unnecessary duplicate infrastructure.

The final architecture should follow the existing codebase conventions.

---

## 23. Completion Report Required From the Implementing AI

After implementation, report:

### Files changed

Example:

```text
assets/wry-discount-auto-apply.js
sections/newsletter.liquid
snippets/cart-drawer.liquid
```

Only list files actually changed.

### Signup hook

Explain exactly how successful email signup is detected.

### Session storage

Confirm:

```text
key: wry_discount_unlocked
storage: sessionStorage
persistent across new sessions: NO
raw customer email stored: NO
```

### Cart events

List the exact theme events/functions used to trigger re-evaluation.

### Discount logic

Confirm all 10 tiers:

```text
WRY100
WRY200
WRY300
WRY400
WRY500
WRY600
WRY700
WRY800
WRY900
WRY1000
```

### Test results

Report PASS/FAIL for the test matrix and the transition tests.

Do not simply say "implemented successfully" without verifying the behavior.

---

## 24. Final Acceptance Criteria

This task is considered complete only when all of the following are true:

- [ ] A visitor without a successful email signup gets no automatic WRY discount.
- [ ] Successful email signup unlocks WRY auto-apply for the current session.
- [ ] The browser stores only a session eligibility flag, not the customer's raw email.
- [ ] The implementation uses `sessionStorage`, not persistent `localStorage`.
- [ ] A cart already containing eligible products receives the correct code immediately after signup.
- [ ] $5,300 automatically selects `WRY500`.
- [ ] $8,500 automatically selects `WRY800`.
- [ ] $9,900 or more automatically selects `WRY1000`.
- [ ] Cart changes automatically upgrade/downgrade the WRY tier.
- [ ] Dropping below $900 removes the managed WRY code.
- [ ] Only one WRY tier is intentionally active at a time.
- [ ] Unrelated discount codes are not automatically deleted.
- [ ] Refreshing within the same active session keeps the feature unlocked.
- [ ] A new browsing session does not automatically restore the entitlement.
- [ ] The existing Shopify email automation is left intact.
- [ ] Normal cart/add-to-cart/checkout behavior remains functional.
- [ ] The implementation does not create an infinite request/render loop.

---

## 25. Final Flow Summary

```text
USER ENTERS EMAIL
        ↓
EMAIL SIGNUP CONFIRMED SUCCESSFUL
        ↓
sessionStorage:
wry_discount_unlocked = true
        ↓
READ CURRENT CART
        ↓
IS SUBTOTAL >= $900?
   ↓ NO            ↓ YES
NO WRY CODE     FIND BEST TIER
                    ↓
              APPLY ONE WRY CODE
                    ↓
          WATCH CART CHANGES
                    ↓
          RE-CALCULATE BEST TIER
                    ↓
        REPLACE WRY CODE IF NEEDED
```

And when the browsing session ends:

```text
SESSION ENDS
        ↓
TEMPORARY UNLOCK STATE IS NOT PERSISTED
        ↓
RETURNING VISIT
        ↓
NO AUTOMATIC WRY DISCOUNT
        ↓
USER MUST COMPLETE EMAIL SIGNUP AGAIN
TO RE-ENABLE AUTO-APPLY
```
