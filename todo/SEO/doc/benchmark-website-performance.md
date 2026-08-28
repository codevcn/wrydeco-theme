# Wrydeco Homepage Performance Benchmark

Benchmark date: 2026-08-28

Target URL: https://wrydeco.com/

Tooling:

- Lighthouse CLI, lab test against the live storefront.
- Mobile run: Lighthouse 13.4.1 default mobile profile.
- Desktop run: Lighthouse 12.8.2 desktop preset.

Note: This is a lab benchmark for regression control and prioritization. It does not replace field Core Web Vitals from Google Search Console or CrUX.

## Summary

| Profile | Performance | FCP | LCP | TBT | CLS | Speed Index | Requests | Transfer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mobile | 33 | 2.6s | 8.0s | 4,150ms | 0 | 9.6s | 337 | 8.08 MB |
| Desktop | 57 | 0.9s | 2.6s | 450ms | 0.002 | 3.4s | 366 | 7.04 MB |

## Resource Mix

| Profile | Main weight drivers |
|---|---|
| Mobile | Images: 65 requests / 4.41 MB; Scripts: 87 requests / 2.38 MB; Other: 111 requests / 0.85 MB |
| Desktop | Images remain the largest controlled weight; scripts remain the biggest main-thread risk |

## Top Hosts By Transfer

| Profile | Host | Requests | Transfer |
|---|---|---:|---:|
| Mobile | wrydeco.com | 258 | 5.48 MB |
| Mobile | www.googletagmanager.com | 5 | 0.77 MB |
| Mobile | newassets.hcaptcha.com | 3 | 0.62 MB |
| Mobile | cdn.shopify.com | 11 | 0.62 MB |
| Mobile | connect.facebook.net | 2 | 0.22 MB |
| Desktop | wrydeco.com | 285 | 4.44 MB |
| Desktop | www.googletagmanager.com | 5 | 0.77 MB |
| Desktop | newassets.hcaptcha.com | 3 | 0.62 MB |
| Desktop | cdn.shopify.com | 11 | 0.62 MB |
| Desktop | connect.facebook.net | 2 | 0.22 MB |

## Lighthouse Opportunities

| Profile | Opportunity | Estimated savings |
|---|---|---:|
| Mobile | Reduce unused JavaScript | 792 KiB |
| Desktop | Reduce unused JavaScript | 796 KiB |
| Desktop | Properly size images | 234 KiB |
| Desktop | Defer offscreen images | 45 KiB |
| Desktop | Avoid serving legacy JavaScript to modern browsers | 36 KiB |

## Interpretation

The mobile score is constrained mainly by long LCP and high TBT. The page is visually stable, but heavy image inventory, many scripts, and third-party/app code are making the first experience expensive.

The desktop score is healthier, but still script-heavy. Request count is high on both profiles, so the next meaningful improvements should focus on reducing or deferring nonessential JavaScript, then tightening image delivery.

## Recommended Next Fix Order

1. Keep hero/LCP eager and verify the final deployed hero image renders with explicit dimensions, responsive source, and meaningful alt.
2. Audit third-party/app scripts loaded on the homepage and remove or delay anything not needed before interaction.
3. Reduce below-fold image count where possible, especially duplicate product/gallery frames rendered in the initial HTML.
4. Ensure below-fold images stay lazy-loaded and are sized close to their rendered dimensions.
5. Re-run Lighthouse mobile and desktop after deployment, then compare with GSC/CrUX once field data updates.

## Raw Outputs

Raw Lighthouse JSON files are stored in:

- `todo/SEO/doc/performance-benchmark-raw/wrydeco-home-mobile.json`
- `todo/SEO/doc/performance-benchmark-raw/wrydeco-home-desktop.json`
