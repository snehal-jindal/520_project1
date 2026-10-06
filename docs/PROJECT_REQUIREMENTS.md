# Project requirements and implementation

Source rechecked: user-supplied Project1.pptx, slide 2. These are the assignment constraints the user asked the project to follow.

| Requirement | Implementation / scope |
|---|---|
| Predict hourly temperature measured at RDU airport | Routine airport reports representing their clock-hour labels; actual timestamps retained; Fahrenheit convention accepted by the user. |
| Midnight September 17 through 11pm September 30 | User specified 2026 Raleigh time: 336 labels, September 17 00:00 EDT through September 30 23:00 EDT. |
| Any data from before September 17 midnight | Guarded training snapshot contains only earlier observations. Archived GFS is pre-origin guidance; separate post-period observations are used only for evaluation. |
| Any inputs/features; any model(s) | Three candidates and explicit input/reference/availability policies documented. |
| MUST include one linear regression and one other model | Ridge linear regressions and histogram gradient boosting are implemented and evaluated. |
| Code repository | Data snapshots, raw final actuals and download details, code, dependencies, settings, tests, results and reproduction commands included. |
| Presentation: inputs, pipeline, features, models, evaluation, performance | Code/evidence ready; student-authored presentation is a later separate deliverable. |
| Writeup: 2–4 pages; approach and application of class concepts | Student-authored deliverable remains outside this code-completion task. |
| AI allowed for coding; writing/slides must be students' own | README/reports are working evidence, not a replacement for graded student writing/slides. |
| Deliverables due October 7 | Repository/code completion now; student-authored deliverables and course submission follow. |

The slide does not prescribe units, exact clock-hour versus routine-report sampling, grading metric, file layout or slide count. The agreed project convention is routine report in Fahrenheit; primary metric MAE, secondary RMSE and signed bias. Do not claim these choices were separately stated by the instructor. In September Raleigh uses EDT (UTC−4); fixed EST would shift labels by an hour.

Forecasts are simulated under the September 17 information cutoff; do not claim real-time issuance. Final actual observations are answer keys, never prediction inputs. The submitted choice is recorded before the final-validation commit; accuracy is reported for every candidate without changing the submitted choice afterward.

Original deck redistribution is separate from extracting requirements and is not performed here.
