# CONTEXT.md — WRYDECO Business & Website Context

Purpose: Reference file for AI Coding Agents building the WRYDECO website.

Scope: Business context, product strategy, audience, content structure, routes, data models, conversion goals, SEO, analytics, and implementation constraints.

Out of scope: Visual design, theme, colors, typography, spacing, animation style, and aesthetic direction. Use `DESIGN.md` for all visual/UI decisions.

---

## 1. Brand Snapshot

WRYDECO is a premium handcrafted natural wood furniture brand positioned between organic art, sculptural furniture, and luxury bespoke interiors.

Core idea:

> Nature wrote the prologue. You write the legacy.

WRYDECO should feel less like a normal furniture store and more like a curated gallery of functional wooden artworks.

The brand sells statement pieces for high-income homeowners, collectors, and interior designers who want furniture with material authenticity, craft story, rarity, and long-term value.

---

## 2. Brand Positioning

WRYDECO is not positioned as cheap, mass-market, or generic home decor.

Positioning:

- Luxury artisan furniture
- Handcrafted natural solid wood
- Bespoke and made-to-order capability
- Organic + sculptural product DNA
- Gallery-style product storytelling
- High-touch consultation for premium buyers
- DTC first, then designer/B2B expansion

Primary difference from mid-market competitors:

- Higher price tier
- Stronger craft story
- More artistic product framing
- More emphasis on bespoke commissions
- More premium customer consultation

---

## 3. Business Goals

The website must support these goals:

1. Build trust for a new premium furniture brand.
2. Convert visitors into consultation leads, product inquiries, or purchases.
3. Present products as collectible functional art, not commodity furniture.
4. Explain craftsmanship, materials, provenance, and customization clearly.
5. Make it easy to browse by category, style, room, artist, and product type.
6. Support future scaling into interior designer and trade customers.
7. Keep the technical structure simple enough to maintain and extend.

---

## 4. Target Audiences

### 4.1 Primary: High-Income DTC Homeowners

Profile:

- Age: roughly 28–55
- Household income: upper-middle to high-income
- Own or design premium homes
- Care about natural materials, interiors, and uniqueness

Needs:

- Statement furniture that feels personal
- Trust in craftsmanship and durability
- Clear product sizing and material details
- Confidence before buying expensive furniture online
- Option to ask for design advice before purchase

Content that works:

- Lifestyle imagery
- Product story
- Artist/maker story
- Process video/photo
- Customer testimonials
- Room inspiration
- Clear consultation CTA

### 4.2 Secondary: Interior Designers / Design Studios

Profile:

- Residential or boutique commercial designers
- Need reliable custom furniture partners
- Care about specs, materials, timelines, and customization options

Needs:

- Trade-friendly product information
- Custom sizing and finish options
- Project inquiry flow
- Reliable communication
- Portfolio/inspiration references

### 4.3 Tertiary: Art Furniture Collectors

Profile:

- Buyers who see furniture as collectible functional art
- Value rarity, sculptural form, provenance, and artistic authorship

Needs:

- Gallery-style presentation
- Artwork name separate from SEO/product name
- Artist attribution
- Limited/unique piece framing
- Premium storytelling

---

## 5. Product Strategy

### 5.1 Product DNA

Core DNA:

- Organic
- Sculptural
- Natural wood
- Functional art
- Bespoke-capable
- Long-lasting heirloom quality

### 5.2 Hero Category: Rustic Tree-Branch Furniture

Hero products include tree-inspired shelves, branch-style shelving, coat racks, and wall storage.

Why this category matters:

- Visually distinctive
- Easier for customers to understand
- Strong craft and nature story
- Good entry point into the WRYDECO world

Expected price range:

- Roughly `$2K–$6K`

### 5.3 Supporting Category: Organic & Sculptural Furniture

Supporting products include live-edge consoles, sculptural shelves, organic tables, and asymmetrical carved pieces.

Expected price range:

- Roughly `$2K–$15K+`

### 5.4 Custom Commission

Custom projects can include modified dimensions, finish changes, wood selection, custom forms, and project-specific design.

Expected price range:

- Roughly `$6K–$25K+`

---

## 6. Value Proposition

Every key page should support at least some of these proof points:

- Handcrafted by skilled artisans
- Solid natural wood, not cheap composite furniture
- Organic forms guided by the wood itself
- Each piece has unique grain, shape, and character
- Designed to last for decades and become an heirloom
- Customization available for serious buyers
- Consultation available before purchase
- Transparent material and process storytelling

Avoid sounding like a generic furniture warehouse.

---

## 7. Brand Voice

Tone:

- Premium
- Calm
- Poetic but not vague
- Confident
- Craft-focused
- Gallery-like
- Trustworthy

Use phrases like:

- handcrafted natural wood furniture
- sculptural wood furniture
- organic form
- functional art
- bespoke commission
- made for your space
- crafted to last generations
- curated piece
- artist / maker / artisan

Avoid phrases like:

- cheap
- budget
- mass-produced
- factory-style
- trendy fast furniture
- discount-first messaging

---

## 8. Website Pages

Required core routes:

- `/` — Home
- `/shop` — Shop / Collections
- `/collections/[slug]` — Collection page
- `/products/[slug]` — Product detail
- `/inspiration` — Room ideas / inspiration
- `/inspiration/[slug]` — Room detail
- `/customization` — Custom design service
- `/artists` — Artist / maker listing
- `/artists/[slug]` — Artist profile
- `/about` — Brand story
- `/contact` — Contact form
- `/faq` — FAQ
- `/blog` — Blog listing
- `/blog/[slug]` — Blog article

Optional later routes:

- `/trade` — Interior designer / trade program
- `/commissions` — Past custom projects
- `/materials` — Wood and finish guide

---

## 9. Home Page Requirements

Home page must communicate the brand quickly and push users toward product browsing or consultation.

Required sections:

1. Hero with brand story and primary CTA.
2. Featured products: 3–5 key products.
3. Gallery/product spotlight with artwork name + artist attribution.
4. Meet the Makers / Artists preview.
5. Customer testimonials.
6. Customization / consultation CTA.
7. FAQ snapshot.

Primary CTAs:

- Shop the Collection
- Request a Consultation
- Explore Custom Work

---

## 10. Shop / Collections Requirements

Shop pages must support browsing and filtering.

Required features:

- Product grid
- Collection/category navigation
- Filters by category, room, style, material, artist, price range
- Sort by relevance, price, newest
- Breadcrumbs
- Product cards with quick view or quick action

Product card should show:

- Artwork name
- Product/SEO name
- Artist/maker
- Price or starting price
- Main image
- Material/style tags

---

## 11. Product Detail Requirements

Product detail pages are critical for conversion.

Required content:

- Product gallery with multiple angles and lifestyle images
- Artwork name
- Product/SEO title
- Artist/maker attribution
- Price or starting price
- Dimensions
- Materials
- Finish
- Availability / made-to-order status
- Add to Cart or Inquiry CTA
- Quantity selector if product is purchasable
- Private Design Consultant CTA
- Process video or process image carousel
- Materials & care section
- Shipping & returns summary
- Related products
- Customer reviews

Important: For premium or custom-heavy products, consultation/inquiry can be more important than direct checkout.

---

## 12. Inspiration Requirements

The Inspiration section helps users imagine products in rooms.

Required features:

- Room idea cards
- Filters by room and style
- Room detail pages
- Linked products used in each room
- Styling tips

Room types:

- Living Room
- Dining Room
- Bedroom
- Home Office
- Entryway
- Bathroom
- Boutique Commercial

Style tags:

- Organic Modern
- Rustic
- Japandi
- Minimalist
- Biophilic
- Farmhouse
- Gallery Home

---

## 13. Customization Requirements

Customization page must generate qualified leads.

Required sections:

1. Hero explaining custom design for a specific space.
2. Three-step process: Consultation → Production → Delivery.
3. Past custom examples or before/after gallery.
4. Customization FAQ.
5. Consultation form.

Consultation form fields:

- Name
- Email
- Phone
- Country / location
- Room type
- Desired product type
- Approximate dimensions
- Budget range
- Timeline
- Message
- File/image upload optional

Lead form must be easy to connect to email/CRM later.

---

## 14. About Page Requirements

About page must build trust.

Required sections:

- Brand story
- Philosophy of natural wood and craft
- Artisan/team profiles
- Material sourcing statement
- Vietnam craftsmanship story
- Transparency/process explanation

No fake certificates or unsupported claims.

---

## 15. Contact & FAQ Requirements

FAQ categories:

- Shipping
- Custom orders
- Materials and care
- Returns
- Payments
- Production timeline
- Consultation

Contact page should include:

- Contact form
- Email block
- Support hours
- Business/location note if available

---

## 16. Blog Requirements

Blog should support SEO and trust-building.

Topics:

- Behind the scenes
- Wood care guides
- Styling tips
- Customer stories
- Artist/maker stories
- Room inspiration
- Custom project breakdowns

Blog posts should link to relevant products, collections, inspiration pages, and consultation CTA.

---

## 17. Suggested Content Models

### Product

```ts
type Product = {
  id: string;
  slug: string;
  artworkName: string;
  seoTitle: string;
  description: string;
  price: number | null;
  startingPrice: number | null;
  category: string;
  roomTypes: string[];
  styles: string[];
  materials: string[];
  artistId: string;
  dimensions: string;
  finishOptions: string[];
  images: string[];
  processMedia?: string[];
  isCustomizable: boolean;
  availability: "in_stock" | "made_to_order" | "custom_only";
};
```

### Artist

```ts
type Artist = {
  id: string;
  slug: string;
  name: string;
  role: string;
  specialties: string[];
  bio: string;
  portraitUrl: string;
};
```

### RoomIdea

```ts
type RoomIdea = {
  id: string;
  slug: string;
  title: string;
  roomType: string;
  style: string;
  image: string;
  productIds: string[];
  tips: string[];
};
```

### ConsultationRequest

```ts
type ConsultationRequest = {
  name: string;
  email: string;
  phone?: string;
  location?: string;
  roomType?: string;
  productType?: string;
  dimensions?: string;
  budgetRange?: string;
  timeline?: string;
  message: string;
  attachments?: string[];
};
```

---

## 18. SEO Requirements

Every indexable page should include:

- Unique title
- Meta description
- Canonical URL
- Open Graph title/description/image
- Structured data where relevant

Recommended schema:

- Product schema for product pages
- Organization schema for brand
- FAQPage schema for FAQ sections
- BlogPosting schema for blog articles
- BreadcrumbList schema for product/collection/blog pages

SEO keyword themes:

- handcrafted wood furniture
- sculptural wood furniture
- organic wood furniture
- live edge furniture
- tree branch shelf
- bespoke wood furniture
- luxury artisan furniture
- custom natural wood furniture

---

## 19. Analytics Events

Track these events:

- Page view
- Product view
- Collection filter used
- Product quick view
- Add to cart
- Checkout started
- Consultation CTA clicked
- Consultation form submitted
- Contact form submitted
- Inspiration room viewed
- Artist profile viewed
- Blog post viewed

---

## 20. Technical Requirements

General:

- Mobile responsive from the beginning
- Simple and maintainable architecture
- Fast image loading with optimized responsive images
- Product data should be easy to edit later
- Forms should be ready for email/CRM integration
- Avoid hardcoding product data inside components when possible
- Keep business content separate from visual design config

E-commerce:

- Support direct product purchase where product is purchasable
- Support inquiry/consultation flow where product is custom or high-ticket
- Allow future integration with Shopify, headless commerce, or custom backend

Forms:

- Validate required fields
- Show success/error states
- Prevent duplicate submissions
- Store or send consultation/contact request payloads cleanly

---

## 21. Business Rules for AI Agent

Do:

- Build the website around premium trust and lead generation.
- Treat products as gallery pieces with artist attribution.
- Keep artwork name separate from SEO/product name.
- Make consultation CTA visible on key pages.
- Use product/artist/style/room data models consistently.
- Keep the system flexible for future product expansion.

Do not:

- Make WRYDECO look like a budget furniture shop.
- Replace business context with visual assumptions.
- Invent certificates, awards, reviews, or sustainability claims.
- Hide important price, size, material, or shipping information.
- Put all content directly inside UI components.
- Overcomplicate the backend before the store needs it.

---

## 22. Acceptance Checklist

The implementation is on-context if:

- The site clearly presents WRYDECO as luxury handcrafted natural wood furniture.
- The site supports both shopping and consultation lead generation.
- Product pages include material, sizing, maker, story, and consultation CTA.
- Shop pages support useful filtering by room, style, category, artist, and price.
- Inspiration pages connect room ideas back to products.
- Customization page captures qualified project leads.
- SEO metadata and analytics events are planned.
- Design decisions are left to `DESIGN.md`.
