# Dashboard — Build Notes

The dashboard is **generated in code** by `src/build_pbix.py`
(using [pbix-mcp](https://github.com/d0nk3yhm/pbix-mcp), pure Python —
no Power BI Desktop needed). Open `output/job-market-dashboard.pbix`
in Power BI Desktop to view / interact.

## Model

- **Jobs** (one row per posting): url, title, company, location, source,
  job_type, salary, posted_at, fit_score, fit_reasons, skills
- **JobSkills** (one row per posting × skill): url, skill
- Relationship: JobSkills[url] → Jobs[url] (many to one)

## Measures (DAX)

- `Posting count = COUNTROWS(Jobs)`
- `Avg fit score = AVERAGE(Jobs[fit_score])`
- `Top matches = COUNTROWS(FILTER(Jobs, Jobs[fit_score] >= 10))`
- `Skill mentions = COUNTROWS(JobSkills)`

## Page — "Overview" (1280×720)

| Visual | Position | Binding |
|---|---|---|
| Title textbox | top | — |
| Card: Total postings | row 1 | Jobs[Posting count] |
| Card: Avg fit score | row 1 | Jobs[Avg fit score] |
| Card: Top matches | row 1 | Jobs[Top matches] |
| Slicer: Location | row 1 | Jobs[location] |
| Bar: Postings by location | row 2 | Category=location, Y=Posting count (desc) |
| Bar: Skill mentions | row 2 | Category=skill, Y=Skill mentions (desc) |
| Table: postings by fit | bottom | title, company, location, fit_score (fit_score desc) |

## Theme

- Palette: `#143D5E` navy, `#1B7F79` teal, `#E8A838` amber, `#D95D39`,
  `#6A8EA6`, `#7FB069`, `#5B5EA6`, `#C1666B`
- Page background `#F2F4F7`; cards white with 1px `#E1E6EB` border,
  8px radius, soft drop shadow; table headers navy with white text.
