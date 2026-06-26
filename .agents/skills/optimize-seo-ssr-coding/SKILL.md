---
name: ssr-seo-code
description: Use when implementing or reviewing SEO-critical web code with an SSR-first architecture, including server-rendered content, metadata, canonical URLs, Open Graph, robots.txt, sitemap.xml, rss.xml, image SEO, pagination, UTM handling, and trust pages.
---

# SSR-First SEO Code Skill

## 1. Core Directive

You are an SSR-first technical SEO coding agent.

Your job is to implement, review, and refactor web code so search engines can crawl, understand, index, preview, and rank important pages correctly.

The highest-priority rule is:

**SEO-critical content must be available in the initial server-rendered HTML.**

Client-side rendering is allowed only for non-critical interactivity, personalization, enhancement, analytics, or UI behavior that does not determine the page's core indexable meaning.

Optimize for:

- crawlability
- indexability
- server-rendered primary content
- stable canonical URLs
- unique metadata per page
- semantic HTML
- image SEO
- structured crawl files
- social preview correctness
- trust and transparency signals
- maintainable framework-native implementation

Do not optimize for:

- CSR-only convenience
- hydration-dependent primary content
- generic metadata
- duplicate routes
- fake SEO tags without server-rendered content
- visual output that hides important content from crawlers

## 2. When To Use This Skill

Use this skill when the user asks to:

- write code chuẩn SEO
- review frontend code for SEO issues
- implement SEO for a Next.js, React, Remix, Nuxt, Astro, SvelteKit, or server-rendered web project
- build or fix product pages, category pages, blog pages, landing pages, documentation pages, or homepage SEO
- implement metadata, canonical URLs, Open Graph tags, Twitter cards, robots rules, sitemap files, RSS feeds, or image sitemaps
- fix crawl, index, duplicate content, metadata, pagination, UTM, or SSR/CSR SEO issues
- convert CSR-heavy pages into SSR, SSG, ISR, or server-rendered architecture

Also use this skill when a task involves:

- dynamic route pages that should rank on Google
- e-commerce product or collection pages
- content pages that need share previews
- pages with pagination, filtering, sorting, search parameters, or UTM tracking
- websites with many images that should appear in Google Images

## 3. Out Of Scope

Do not use this skill as the main skill for:

- keyword research only
- backlink outreach only
- ad campaign strategy only
- copywriting without code or page-structure changes
- legal, medical, or financial claims that require domain expert approval
- purely private app screens that are intentionally not indexed
- admin dashboards, carts, checkout pages, user account pages, or authenticated pages unless the task is to prevent indexing

## 4. SSR-First Priority Model

When there is a conflict, follow this priority order:

1. Server-render SEO-critical content.
2. Use correct index/noindex rules.
3. Use one stable canonical URL.
4. Generate unique metadata per page.
5. Preserve semantic HTML and heading structure.
6. Optimize images and media for crawlability, layout stability, and speed.
7. Generate crawl files: `robots.txt`, `sitemap.xml`, optional `rss.xml`, optional `image-sitemap.xml`.
8. Add Open Graph and social metadata.
9. Add interactive client-side enhancements only after the server-rendered foundation is correct.

## 5. Critical SSR Rules

### 5.1 Primary Content Must Render On The Server

For every indexable page, the initial HTML must include the primary content that defines the page.

Examples of primary SEO content:

- product name
- product description
- product price if publicly indexable
- product images and image alt text
- category title and category intro
- article title
- article body or meaningful excerpt
- landing page headline and value proposition
- author name when relevant
- breadcrumbs
- internal links to related important pages

Never make Googlebot wait for hydration to discover the core page meaning.

### 5.2 CSR Is Only For Enhancements

Client Components, client-side state, `useEffect`, browser APIs, and client fetches are allowed only for:

- sliders
- tabs
- modals
- menus
- filters that enhance an already crawlable base page
- image galleries when the primary image and core content are already server-rendered
- cart actions
- wishlist actions
- analytics
- personalization that does not replace canonical content
- non-indexable authenticated UI

### 5.3 CSR Red Flags

Treat the following as SEO failures for indexable pages:

- the page root is marked `use client` without a strong reason
- the product, category, blog, or landing page content is fetched only in `useEffect`
- the server HTML contains only a loading spinner or skeleton for the main content
- metadata depends on client state
- canonical URL is computed only in the browser
- the page title is updated only after hydration
- internal links are hidden behind client-only rendering
- images exist only after client-side JavaScript runs
- route content is unavailable when JavaScript is disabled

### 5.4 Acceptable Rendering Modes

Prefer these rendering modes for SEO pages:

1. SSG: static generation for stable pages.
2. ISR: static generation with scheduled or on-demand revalidation for product, category, and blog pages.
3. SSR: per-request rendering for frequently changing or personalized-but-indexable public pages.
4. Hybrid SSR plus client enhancement: server-render the canonical content, then enhance with interactive UI.

Avoid pure CSR for indexable pages.

## 6. Required Context Inference

Before editing code, identify:

1. Framework and router: Next.js App Router, Next.js Pages Router, Remix, Nuxt, Astro, SvelteKit, Express template, or another stack.
2. Page type: homepage, product page, category page, article, landing page, search results, filtered page, paginated page, or utility page.
3. Indexing intent: `index` or `noindex`.
4. Canonical strategy: self-canonical, canonical to clean URL, canonical to parent URL, or canonical to another language/region variant.
5. Data source: CMS, database, API, local files, Shopify, custom backend, static config.
6. Rendering mode: SSG, ISR, SSR, or CSR-only currently requiring refactor.
7. Existing SEO utilities: metadata helpers, site config, sitemap generator, route helpers, image helpers.
8. Existing conventions: folder structure, naming, import aliases, code style, TypeScript strictness.

If relevant files are available, inspect them first. Do not guess structure that can be read from the project.

## 7. Execution Workflow

1. Inspect the target route, layout, metadata helpers, data-fetching code, and existing SEO files.
2. Determine whether the page should be indexable.
3. Ensure SEO-critical data is fetched on the server.
4. Ensure the initial HTML contains the primary content.
5. Generate unique `title` and `description` for the page.
6. Generate exactly one canonical URL.
7. Add or fix `robots` metadata.
8. Add Open Graph metadata for shareable pages.
9. Add Twitter card metadata when the framework or project convention supports it.
10. Verify semantic HTML: `main`, `article`, `section`, logical headings, meaningful links, breadcrumb when appropriate.
11. Optimize meaningful images with stable dimensions, accurate `alt`, and correct loading priority.
12. Update or create `robots.txt`.
13. Update or create `sitemap.xml` with canonical indexable URLs only.
14. Add `rss.xml` for blogs, news, articles, or frequently updated public content.
15. Add `image-sitemap.xml` or image entries when images are SEO-important.
16. Handle pagination, filters, sorting, and UTM parameters without creating duplicate-content traps.
17. Run the pre-flight checklist before final output.

## 8. Metadata Rules

### 8.1 Title

Every indexable page must have a unique, specific title.

Rules:

- Include the main topic or keyword naturally.
- Keep it concise and readable.
- Avoid generic values such as `Home`, `Product`, `Blog`, or `Untitled`.
- For paginated pages, include the page number.
- For product pages, include the product name and optionally the brand or key attribute.
- For category pages, include the category name and optionally the store or site name.

### 8.2 Description

Every indexable page should have a unique description.

Rules:

- Summarize the page clearly.
- Encourage clicks without clickbait.
- Avoid keyword stuffing.
- For paginated pages, make the description distinct with the page number.
- Do not reuse the exact same description across many important pages.

### 8.3 Keywords Meta

The `keywords` meta tag may be supported if the project already uses it, but it must not be treated as the main SEO mechanism.

Rules:

- Use only relevant terms.
- Do not stuff keywords.
- Do not spend implementation effort on keywords while SSR, canonical, title, description, and content are broken.

### 8.4 Robots Meta

Each important page should have an intentional robots decision.

Use `index, follow` for canonical public pages that should rank.

Use `noindex, follow` for pages that users may visit but should not appear in search results.

Common `noindex` candidates:

- internal search pages
- cart pages
- checkout pages
- account pages
- admin pages
- temporary campaign variants
- thin filter combinations
- duplicate tracking URLs

Do not rely on `robots.txt` as a replacement for `noindex`.

## 9. Canonical URL Rules

### 9.1 General Canonical Rules

Every indexable page must have exactly one canonical URL.

Canonical URLs must:

- be absolute URLs
- use HTTPS in production
- point to the final `200` destination
- avoid redirect targets
- avoid `404`, `500`, blocked, or unauthorized pages
- match the intended indexable version of the page
- be consistent with internal links and Open Graph `og:url`

### 9.2 Self-Canonical Rules

Use self-canonical for:

- canonical article pages
- canonical product pages
- canonical landing pages
- canonical category pages with unique value
- paginated pages where each page contains distinct content
- language or region variants when paired with proper `hreflang`

### 9.3 Pagination Rules

For pagination, do not canonical every page to page 1.

Correct pattern:

- `/category/shoes?page=1` canonicalizes to `/category/shoes?page=1` or the clean page-1 URL if that is the project convention.
- `/category/shoes?page=2` canonicalizes to `/category/shoes?page=2`.
- `/category/shoes?page=3` canonicalizes to `/category/shoes?page=3`.

Each paginated page should have distinct title and description using the page number.

Example title pattern:

```txt
Nike Shoes - Page 2 | Example Store
```

### 9.4 Sorting, Tracking, And Duplicate Parameters

Parameters that do not materially change the canonical content should canonicalize to the clean URL.

Examples:

- `?utm_source=facebook`
- `?utm_medium=cpc`
- `?utm_campaign=summer-sale`
- `?ref=newsletter`
- `?sort=price-asc`
- `?sort=price-desc`
- `?session_id=abc123`

If a filter creates a meaningful landing page with distinct search demand and unique content, it may self-canonical.

Example:

- `/shoes/nike-red-running-shoes` may self-canonical if it is intentionally built as an indexable page.
- `/shoes?sort=price-asc` should usually canonicalize to `/shoes`.

### 9.5 Canonical Anti-Patterns

Never create:

- multiple canonical tags on one page
- relative canonical URLs in production
- canonical URLs pointing to redirected pages
- canonical URLs pointing to `404`
- canonical URLs conflicting with `noindex`
- canonical tags generated only on the client
- canonical tags that collapse meaningful paginated pages into page 1

## 10. Open Graph And Social Preview Rules

Every shareable page should include Open Graph metadata.

Required Open Graph fields:

- `og:title`
- `og:description`
- `og:image`
- `og:url`
- `og:type`

Rules:

- `og:url` should match the canonical URL.
- `og:image` should be high quality.
- Prefer `1200x630` images for general social sharing.
- Use `article` for articles and blog posts.
- Use `product` when the platform supports product pages and the project convention uses it.
- Use `website` for homepage and broad landing pages.
- Do not let social crawlers guess the title, description, or image.

Add Twitter card metadata when supported by the project convention.

## 11. Semantic HTML And Content Rules

### 11.1 Main Content Placement

Place the main content early in the HTML structure.

Use semantic containers:

- `main` for the page's primary content
- `article` for articles, blog posts, and standalone editorial content
- `section` for meaningful page sections
- `nav` for navigation and breadcrumbs
- `aside` for supplementary content
- `footer` for footer content

Do not put the main content inside a table unless the content is actually tabular data.

### 11.2 Heading Structure

Rules:

- Use one clear `h1` for the main topic of the page.
- Use `h2` for major sections.
- Use `h3` for subsections under `h2`.
- Do not choose headings only for visual size.
- Do not skip heading levels for styling convenience.
- Important keywords should appear naturally in headings when relevant.

### 11.3 Internal Links

Internal links should help users and crawlers discover important pages.

Rules:

- Use real anchor links with `href` for crawlable navigation.
- Avoid hiding important links behind click-only JavaScript.
- Link to related products, categories, articles, and parent pages when useful.
- Use descriptive anchor text.
- Do not use vague repeated anchors such as `click here` for important internal links.

### 11.4 Breadcrumbs

Use breadcrumbs when pages are part of a hierarchy.

Good candidates:

- product pages
- category pages
- documentation pages
- blog posts inside categories

Breadcrumbs should:

- render on the server
- use real links
- reflect the page hierarchy
- help users navigate upward
- optionally include structured data if the project supports it

## 12. Image SEO Rules

### 12.1 File Names

Image file names should be descriptive and relevant.

Good:

```txt
nike-air-max-2025-red-side-view.webp
```

Bad:

```txt
IMG_12345.png
```

### 12.2 Formats And Compression

Prefer modern formats:

- WebP
- AVIF

Use PNG only when transparency or lossless requirements justify it.

Do not serve very large original images and shrink them only with CSS.

### 12.3 Dimensions And Layout Stability

Every meaningful image should include width and height or use a framework image component that reserves layout space.

This prevents layout shift and improves user experience.

### 12.4 Alt Text

Every meaningful image must have accurate `alt` text.

Rules:

- Describe the image content clearly.
- Include relevant keywords only when natural.
- Do not keyword-stuff alt text.
- Use empty `alt=""` only for decorative images.

### 12.5 Loading Strategy

Rules:

- Above-the-fold important images should load eagerly or use framework priority settings.
- Below-the-fold images should use lazy loading.
- Do not lazy-load the main hero/product image if it is critical to the first viewport.

### 12.6 Image Sitemap

Use an image sitemap when:

- the website has many SEO-important images
- images are part of product galleries
- images are loaded through JavaScript
- the site depends on traffic from Google Images
- the project is e-commerce, editorial, photography, portfolio, travel, food, or visual catalog content

Only include SEO-important images. Do not include icons, tiny decorative images, or minor background assets.

## 13. robots.txt Rules

`robots.txt` must live at the website root.

Example location:

```txt
https://example.com/robots.txt
```

Use it to guide crawler access, not as a security mechanism.

Rules:

- Include a `Sitemap` directive pointing to the sitemap URL.
- Do not block important indexable pages.
- Block low-value crawl areas when appropriate, such as admin routes, internal search, cart, checkout, and temporary test routes.
- Remember that `robots.txt` blocks crawling, not necessarily indexing.
- Use `noindex` when the intent is to keep a page out of search results.

Good default example:

```txt
User-agent: *
Disallow: /admin/
Disallow: /cart/
Disallow: /checkout/
Disallow: /account/
Sitemap: https://example.com/sitemap.xml
```

## 14. sitemap.xml Rules

`sitemap.xml` should list important canonical URLs.

Rules:

- Include only canonical URLs that should be indexed.
- Do not include `noindex` pages.
- Do not include redirected URLs.
- Do not include `404` pages.
- Do not include internal search result pages unless intentionally indexable.
- Include `lastmod` when accurate data exists.
- Split sitemaps when exceeding platform or protocol limits.
- Use sitemap index files for large websites.

Common sitemap groups:

- homepage
- static pages
- product pages
- category pages
- blog posts
- documentation pages
- image sitemap
- news sitemap for eligible news sites

## 15. rss.xml Rules

Add RSS when the website publishes recurring public updates.

Good candidates:

- blog
- news
- changelog
- articles
- tutorials
- product updates

RSS entries should include:

- title
- link to canonical page
- description or excerpt
- publication date

RSS is not a replacement for sitemap, but it can help users, feed readers, aggregators, automation tools, and crawlers discover new content.

## 16. EEAT And Trust Rules

For public websites, especially commercial or content websites, ensure trust signals are present and crawlable.

Recommended pages:

- About
- Contact
- Privacy Policy
- Terms & Conditions
- Return or refund policy for e-commerce
- Shipping policy for e-commerce
- Author pages for editorial content

Trust implementation rules:

- Use HTTPS.
- Show clear business or author information when relevant.
- Show contact information when relevant.
- Cite sources for factual claims when the project content requires it.
- For product reviews or experience content, include real experience signals when available.
- For YMYL topics, avoid unsupported claims and require expert review.

## 17. External Link Rules

For external links that open in a new tab, use:

```html
rel="noopener noreferrer"
```

Use descriptive anchor text.

Do not mark all external links as `nofollow` by default unless the project has a clear policy.

Use `sponsored` or `nofollow` only when appropriate for ads, paid links, affiliate links, or untrusted user-generated content.

## 18. UTM Handling Rules

UTM parameters are for analytics and campaign attribution.

They do not change the actual page content.

Rules:

- Do not create separate indexable pages for UTM variants.
- Canonicalize UTM URLs to the clean canonical URL.
- Keep tracking logic separate from canonical logic.
- Do not put UTM URLs into sitemap.
- Do not use UTM URLs as `og:url`.

Example:

Requested URL:

```txt
https://example.com/products/nike-air-max?utm_source=facebook&utm_medium=cpc
```

Canonical URL:

```txt
https://example.com/products/nike-air-max
```

## 19. Next.js App Router Rules

When working in Next.js App Router, follow these rules.

### 19.1 Server Components By Default

Pages and layouts should be Server Components by default.

Do not add `use client` to a page or layout unless browser-only behavior is required.

If interactivity is needed, isolate it into leaf Client Components.

Good structure:

```txt
app/products/[slug]/page.tsx                 server-rendered SEO page
app/products/[slug]/ProductGallery.tsx       client component for gallery interaction
app/products/[slug]/AddToCartButton.tsx      client component for cart action
app/products/[slug]/metadata.ts              optional metadata helper
```

### 19.2 Server Data Fetching

Fetch SEO-critical data in the server page, server layout, or server utility.

Good:

```tsx
export default async function ProductPage({ params }: ProductPageProps) {
  const product = await getProductBySlug(params.slug)

  if (!product) {
    notFound()
  }

  return (
    <main>
      <article>
        <h1>{product.name}</h1>
        <p>{product.description}</p>
      </article>
    </main>
  )
}
```

Bad:

```tsx
'use client'

export default function ProductPage() {
  const [product, setProduct] = useState<Product | null>(null)

  useEffect(() => {
    fetch('/api/products/current')
      .then((response) => response.json())
      .then((data) => setProduct(data))
  }, [])

  if (!product) {
    return <main>Loading product...</main>
  }

  return <main><h1>{product.name}</h1></main>
}
```

### 19.3 Metadata

Use `generateMetadata` for dynamic route metadata.

Good:

```tsx
export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const product = await getProductBySlug(params.slug)

  if (!product) {
    return {
      title: 'Product Not Found',
      robots: {
        index: false,
        follow: false,
      },
    }
  }

  const canonicalUrl = `${siteConfig.url}/products/${product.slug}`

  return {
    title: product.seoTitle || product.name,
    description: product.seoDescription || product.description,
    alternates: {
      canonical: canonicalUrl,
    },
    robots: {
      index: true,
      follow: true,
    },
    openGraph: {
      title: product.seoTitle || product.name,
      description: product.seoDescription || product.description,
      url: canonicalUrl,
      type: 'website',
      images: [
        {
          url: product.ogImageUrl || product.imageUrl,
          width: 1200,
          height: 630,
          alt: product.name,
        },
      ],
    },
  }
}
```

### 19.4 Sitemap

Use `app/sitemap.ts` when appropriate.

Example:

```tsx
import type { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const products = await getIndexableProducts()
  const posts = await getPublishedPosts()

  return [
    {
      url: `${siteConfig.url}/`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    ...products.map((product) => ({
      url: `${siteConfig.url}/products/${product.slug}`,
      lastModified: product.updatedAt,
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    })),
    ...posts.map((post) => ({
      url: `${siteConfig.url}/blog/${post.slug}`,
      lastModified: post.updatedAt,
      changeFrequency: 'monthly' as const,
      priority: 0.7,
    })),
  ]
}
```

### 19.5 Robots

Use `app/robots.ts` when appropriate.

Example:

```tsx
import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/cart/', '/checkout/', '/account/'],
    },
    sitemap: `${siteConfig.url}/sitemap.xml`,
  }
}
```

### 19.6 Static Generation And Revalidation

Use `generateStaticParams` for known stable dynamic pages when appropriate.

Use ISR or revalidation for public content that changes but does not require per-request rendering.

Do not force per-request SSR when static generation or ISR is better for performance and freshness.

Do not force static generation when content must be accurate per request.

## 20. Next.js Pages Router Rules

When working in Next.js Pages Router:

- Use `getStaticProps` for stable SEO pages.
- Use `getStaticPaths` for known dynamic routes.
- Use `getServerSideProps` for per-request SEO pages.
- Use `next/head` for metadata only when App Router metadata APIs are not available.
- Do not fetch SEO-critical content only after mount.

Good:

```tsx
export const getStaticProps: GetStaticProps<ProductPageProps> = async (context) => {
  const slug = String(context.params?.slug)
  const product = await getProductBySlug(slug)

  if (!product) {
    return {
      notFound: true,
    }
  }

  return {
    props: {
      product,
    },
    revalidate: 3600,
  }
}
```

## 21. React SPA Refactor Rules

If the project is a pure React SPA and the target pages need SEO, recommend or implement a server-rendered solution.

Acceptable paths:

- migrate SEO pages to Next.js, Remix, Astro, Nuxt, or another SSR framework
- pre-render public routes at build time
- introduce server rendering for marketing, product, category, and blog pages
- keep the SPA for authenticated app areas only

Do not pretend that adding client-side meta tags to a CSR-only page fully solves SEO.

## 22. E-Commerce Page Rules

### 22.1 Product Pages

Product pages should server-render:

- product name
- canonical product URL
- description
- primary product image
- image alt text
- price when public
- availability when public
- important variant information when indexable
- breadcrumbs
- related internal links

Do not render product details only after client fetch.

### 22.2 Category Pages

Category pages should server-render:

- category name
- category description or intro text
- crawlable product links
- pagination links when applicable
- canonical URL
- unique metadata

Filtering rules:

- Index only meaningful filter pages.
- Noindex or canonicalize thin filter pages.
- Sorting parameters usually canonicalize to the base category.

### 22.3 Search Pages

Internal search result pages are usually `noindex, follow` unless the project intentionally creates curated indexable search landing pages.

## 23. Blog And Editorial Page Rules

Blog posts and articles should server-render:

- title
- author when available
- publish date and updated date when available
- article body or meaningful content
- canonical URL
- Open Graph metadata
- internal links
- related articles when useful

Use RSS for blogs and editorial sites with recurring updates.

For EEAT, include author information and sources when the topic requires trust.

## 24. 404 And Error Page Rules

Create a helpful 404 page.

A good 404 page should:

- return the correct HTTP status
- explain that the page was not found
- link to important areas such as homepage, categories, search, or contact
- avoid being indexed as a normal content page

Do not let missing product or article pages return `200` with empty content.

## 25. Banned Patterns

Never output or approve these patterns for SEO-critical pages:

- CSR-only product pages
- CSR-only blog articles
- CSR-only landing page headline and body content
- metadata generated only in the browser
- canonical generated only in the browser
- title changed only with client-side effects
- important links rendered only after hydration
- skeleton-only server HTML for indexable pages
- multiple canonical tags
- missing canonical on indexable pages
- canonical to redirected URL
- canonical to `404`
- generic titles across many pages
- duplicate descriptions across important pages
- Open Graph image missing on shareable pages
- `robots.txt` blocking important pages
- `sitemap.xml` containing `noindex`, redirected, or missing pages
- UTM URLs in sitemap
- tracking URLs as canonical URLs
- keyword-stuffed alt text
- missing width and height on important images
- meaningless image file names for SEO-important images
- hidden text intended only for search engines
- fake content or fake links
- unrelated rewrites while fixing SEO

## 26. Output Requirements For The Agent

When responding to the user after applying this skill:

- State whether the solution is SSR, SSG, ISR, or CSR-enhanced SSR.
- List the files changed or the files that should be changed.
- Explain the canonical strategy.
- Explain the index/noindex strategy.
- Mention sitemap, robots, RSS, or image sitemap changes when relevant.
- Mention any remaining manual checks such as Google Search Console validation.
- Do not claim SEO success without acknowledging that indexing and ranking are ultimately determined by search engines.

If the user asks for code, provide complete code for the requested file or patch.

If the user asks for a review, separate findings into:

- critical SSR/indexing issues
- metadata/canonical issues
- content/semantic HTML issues
- image SEO issues
- crawl file issues
- recommended fixes

## 27. Pre-Flight Checklist

Before final output, verify:

### SSR And Rendering

- SEO-critical content is present in initial server-rendered HTML.
- The page does not depend on `useEffect` for primary content.
- Client Components are isolated to interactive leaf components.
- The page works meaningfully when JavaScript is disabled.
- Missing content returns a proper 404 or intentional noindex state.

### Metadata

- Each indexable page has a unique title.
- Each indexable page has a unique description.
- Robots metadata is intentional.
- Shareable pages have Open Graph metadata.
- `og:url` matches canonical.
- `og:image` is valid and high quality.

### Canonical

- Exactly one canonical URL exists.
- Canonical URL is absolute.
- Canonical URL uses HTTPS in production.
- Canonical URL points to the final `200` page.
- Pagination uses self-canonical where pages are meaningful.
- UTM and tracking URLs canonicalize to clean URLs.

### Semantic HTML

- There is one clear `h1`.
- Heading hierarchy is logical.
- Main content is inside `main`.
- Articles use `article` when appropriate.
- Important internal links are real anchor links.
- Breadcrumbs exist for hierarchical pages when appropriate.

### Images

- Meaningful images have accurate alt text.
- Important images have width and height or reserved layout space.
- Above-the-fold critical images are not incorrectly lazy-loaded.
- Below-the-fold images are lazy-loaded.
- Image file names are descriptive when controlled by the project.
- Image sitemap exists when image SEO is important.

### Crawl Files

- `robots.txt` exists for public websites.
- `robots.txt` points to `sitemap.xml`.
- `robots.txt` does not block important indexable pages.
- `sitemap.xml` includes only canonical indexable URLs.
- `sitemap.xml` excludes `noindex`, redirected, and error URLs.
- `rss.xml` exists for recurring public content when appropriate.

### Trust

- About page exists when relevant.
- Contact page exists when relevant.
- Privacy Policy exists when relevant.
- Terms & Conditions exists when relevant.
- HTTPS is assumed or configured for production.
- Author/source information exists for trust-sensitive content when relevant.

## 28. Final Principle

Technical SEO begins with server-rendered truth.

If crawlers cannot see the page's real content, metadata, links, images, and canonical intent in the initial server response, the page is not SEO-ready, no matter how polished the client-side experience looks after hydration.
