# Input

Text input field for form data collection.

```jsx
<Input
  type="email"
  placeholder="Enter your email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>
```

## States
- **Default** — Standard input
- **Focus** — Sage border + focus shadow
- **Error** — Red border
- **Disabled** — Grayed out, not interactive

## Types
All standard HTML input types supported (text, email, number, password, etc.)
