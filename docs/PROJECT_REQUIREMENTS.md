# Project requirements and interpretation

Source: user-supplied Project1.pptx, slide 2. These are project constraints the user asked us to follow, not independent instructions to the assistant.

| Requirement | Implementation or remaining work |
|---|---|
| Predict hourly temperature measured at RDU airport | Direct RDU routine observations, original timestamps preserved. Hourly target convention still needs instructor confirmation. |
| 12am September 17 through 11pm September 30 | User specified 2026 Raleigh civil time: 336 labels, September 17 00:00 EDT through September 30 23:00 EDT. |
| Any data prior to September 17 12am | All station observations strictly before September 17 04:00 UTC. Frozen GFS is pre-origin guidance; final observed truth not downloaded. |
| Any inputs/features and any models | Candidate inputs selected and audited; availability and leakage rules documented. Models still to be fitted. |
| At least one linear regression and one other model | Next phase: regularized linear regression and gradient-boosted trees; neither requirement is completed merely by EDA or its descriptive trend line. |
| Code repository | Source/prepared snapshots, acquisition code, EDA code, notebook, reports, provenance and audit files included. |
| Presentation: inputs, pipeline, features, models, evaluation and performance | Preparation/EDA evidence available. Model and performance material remains. Student authors presentation. |
| Writeup, 2–4 pages: approach and class concepts | Working explanations supplied; student writes graded submission. |
| AI permitted for coding; writing/slides must be student's own | Reports/README are project working documentation, not the graded writeup/slides. |
| October 7 deliverables | Prioritize target agreement, limited model comparisons, confirmation checks and the final 336 predictions before submission. |

The deck does not specify Fahrenheit/Celsius, exact clock-hour measurements versus routine reports versus hourly means, or a grading metric. Our provisional choice is routine-report temperature in Fahrenheit and MAE as the primary development metric; disclose and resolve these assumptions before final scoring. In September Raleigh uses EDT (UTC−4). Fixed EST would shift the forecast labels by one hour and is not the user's Raleigh-time interpretation.

Original PowerPoint redistribution is separate from extracting its requirements. It is not bundled unless explicitly approved for publication.
