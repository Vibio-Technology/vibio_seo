# Entity Strategy — Knowledge Graph & Topical Authority

Modern SEO rewards entities, not just keywords. Build recognition in Google's Knowledge Graph and establish topical authority through entity relationships.

## 1. What Entities Are

Entities are distinct things Google recognizes: people, places, organizations, products, concepts, events. When Google understands your entity and its relationships, it can surface you in Knowledge Panels, entity carousels, and AI-generated answers.

## 2. Entity Identification

### Map your entity graph:
1. **Core entity:** your brand/organization (e.g., "Jiangsu Zeyusen Carbon Fiber Technology Co., Ltd.")
2. **Product entities:** specific materials, products, SKUs
3. **Attribute entities:** specifications, standards (ISO 9001, ASTM D3039), certifications
4. **Related concept entities:** manufacturing processes (pultrusion, filament winding), applications (wind energy, automotive)
5. **Industry entities:** trade associations, standards bodies, major events

## 3. Entity Optimization

### Consistent naming
- Use the exact same entity name everywhere: website, social profiles, directory listings
- Full legal name for Organization schema; consistent short brand for alternateName
- Same entity name in: JSON-LD, page titles, headings, meta descriptions, visible text

### Entity linking
- Link to authoritative entity sources: Wikipedia, Wikidata, official industry databases
- Use `sameAs` in Organization JSON-LD to link all your official profiles
- Link out to authoritative sources for related entities (standards bodies, industry associations)

### Entity-rich content
- Mention related entities naturally in content
- Define entity relationships explicitly ("X is a type of Y used in Z")
- Use entity attributes as content dimensions (specs, certifications, applications)

## 4. Topical Authority Building

Topical authority = Google trusts you as a comprehensive source on a topic.

### Build the entity hub:
1. Create a pillar page covering the core entity and its relationship to all subtopics
2. Create spoke pages for each related entity/subtopic
3. Link hub → spokes and spokes → hub with descriptive anchors
4. Ensure every page adds unique entity coverage (no thin content)

### Coverage depth signals:
- Content covers all major entity relationships in the topic space
- Multiple content formats (guides, specs, comparisons, FAQs, case studies)
- Regular updates demonstrating ongoing expertise
- External citations from authoritative sources in the same entity space

### Measurement:
- How many entity-related queries do you rank for?
- Are you ranking for the full entity graph or just a subset?
- Do competitors have broader entity coverage?

## 5. Knowledge Graph Optimization

### Organization structured data (essential):
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Full Legal Company Name",
  "alternateName": "ShortBrand",
  "url": "https://www.example.com",
  "logo": "https://www.example.com/logo.png",
  "sameAs": [
    "https://www.linkedin.com/company/...",
    "https://en.wikipedia.org/wiki/...",
    "https://www.wikidata.org/wiki/..."
  ],
  "description": "Concise entity description matching Knowledge Graph",
  "foundingDate": "2008",
  "address": { ... },
  "contactPoint": { ... }
}
```

### Wikipedia / Wikidata presence:
- Wikipedia page (if notable): ensures Knowledge Graph inclusion
- Wikidata entry: even without Wikipedia, adds structured entity data
- Both serve as authoritative `sameAs` references

### Brand SERP optimization:
- Site-name in SERP: `WebSite` JSON-LD `name` + `og:site_name`
- Knowledge Panel: `Organization` JSON-LD + Wikipedia/Wikidata + consistent NAP
- Entity carousel: related entity coverage in content + internal linking

## 6. Tools & Routing

| Need | Route |
|------|-------|
| Schema validation | `seo-schema` |
| Knowledge Graph check | Google search your brand name, observe Knowledge Panel |
| Entity coverage analysis | `seo-cluster` (entity-based clusters) |
| Competitor entity coverage | Manual SERP analysis of competitor topic breadth |
