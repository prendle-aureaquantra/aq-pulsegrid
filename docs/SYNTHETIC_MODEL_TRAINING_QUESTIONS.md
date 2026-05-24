# AQ PulseGrid — Expanded Synthetic Model Training Questions

These prompts are intended for:

- ML model training
- Semantic layer evaluation
- AI copilot testing
- Synthetic RAG datasets
- Vector embedding generation
- Dashboard narration
- Anomaly detection systems
- Operational intelligence simulations

**Machine-readable catalog:** [`datasets/reference/synthetic_questions.yaml`](../datasets/reference/synthetic_questions.yaml) (version 2+)

**Terminology:** In prompts below, *Pulse Score* maps to **City Stress Index** (`city_stress_index`); *CTA delays* maps to **Active Transit Alerts** and `TransitAlertSummary` / `TransitAlertDetail`.

---

## Root cause analysis

- Why did the City Stress Index decline between 4 PM and 6 PM?
- What caused the largest operational disruption today?
- Which signals contributed most to congestion escalation?
- What factors caused airport delays to spike?
- Which combination of events produced anomaly conditions?
- Why did downtown transit delays exceed forecast levels?
- Which metrics deviated furthest from historical norms?
- What caused operational instability in the Loop?
- Which systems amplified weather-related disruptions?
- Why did the anomaly score increase after the Cubs game?

**Semantic hints:** `CityPulseSnapshot`, `AnomalySignals`, `TransitAlertDetail`, `AirportOpsSnapshot`, `CityEventDetail`, time filters on `snapshot_at`.

---

## Comparative intelligence

- Compare today's congestion levels to last Friday.
- Which city has the strongest operational stability this week?
- Compare airport disruptions across major metro areas.
- Which neighborhoods improved most week-over-week?
- Compare event-driven congestion across districts.
- Which transit lines are underperforming relative to baseline?
- Compare current weather impacts versus historical averages.
- Which airports recovered fastest after disruptions?
- Compare City Stress Index trends across cities.
- Which regions demonstrate the highest resilience?

**Semantic hints:** `DimMetro`, `CityPulseSnapshot`, `HexPulseGrid`, `AirportOpsSnapshot`, `ml/pulse_history` (where available).

---

## Temporal patterns

- What time of day produces the highest anomaly frequency?
- Which hours show peak congestion risk?
- How do operational conditions evolve during severe weather?
- What trends emerge during weekend event spikes?
- Which seasonal patterns affect airport operations?
- What recurring timing patterns exist in transit disruptions?
- When are mobility systems most vulnerable?
- Which periods show the largest operational variance?
- What long-term trends are visible in City Stress Index values?
- How does congestion evolve during major festivals?

**Semantic hints:** `snapshot_at`, `AnomalySignals`, `WeatherForecastPeriods`, `CityEventDetail`.

---

## Predictive risk

- Which districts are most likely to experience congestion tomorrow?
- Predict operational instability over the next 12 hours.
- Which weather conditions are most likely to trigger anomalies?
- Forecast transit reliability for the evening rush hour.
- Which airport routes are at highest delay risk?
- Predict neighborhood stress during major events.
- Which systems are most vulnerable to cascading failures?
- What operational conditions may deteriorate overnight?
- Which city metrics indicate elevated future disruption risk?
- Forecast anomaly likelihood by district.

**Note:** Production pipeline today is snapshot + z-score anomalies, not trained forecasts. Use for ML backlog and copilot what-if demos (`roadmap: true` in YAML).

---

## Correlation discovery

- Which weather variables correlate most with transit delays?
- Are airport disruptions correlated with downtown congestion?
- Which event types most strongly impact transit systems?
- What relationships exist between social trends and activity density?
- Which neighborhoods show strongest weather sensitivity?
- Are City Stress Index values correlated with airport congestion?
- Which metrics are most predictive of operational instability?
- What signals best predict nightlife surges?
- Which combinations of variables drive anomaly spikes?
- What operational indicators move together most frequently?

**Semantic hints:** `CityPulseSnapshot`, `TransitAlertSummary`, `TrendInterestSummary`, `WeatherForecastPeriods`, `AirportOpsSnapshot`.

---

## Executive summary

- Generate a summary of today's operational conditions.
- Explain the top operational risks in plain English.
- Summarize major transit disruptions.
- Describe current airport conditions for executives.
- Generate a citywide operational briefing.
- Explain current anomaly conditions for leadership.
- Summarize weather-related impacts across the city.
- Generate a regional risk assessment.
- Explain the top contributors to today's City Stress Index.
- Summarize operational conditions by district.

**Semantic hints:** `CityPulseSnapshot`, `AnomalySignals`, `TransitAlertSummary`, `DimMetro`.

---

## Geospatial reasoning

- Which neighborhoods are operational hotspots?
- Where are anomaly clusters concentrated?
- Which areas demonstrate unusual activity density?
- Which districts are most affected by airport disruptions?
- What regions show elevated congestion propagation?
- Which neighborhoods exhibit highest stress volatility?
- Where are operational recovery rates weakest?
- Which transit corridors generate the largest downstream impacts?
- What regions demonstrate strongest event-driven spikes?
- Which areas show emerging operational instability?

**Semantic hints:** `HexPulseGrid`, `TransitAlertDetail[neighborhood]`, `EventHeatmap`, `CityEventDetail`.

---

## Semantic layer

- What is the average City Stress Index by district?
- Which regions exceed congestion thresholds?
- What is the rolling 7-day anomaly trend?
- Which operational metrics have highest variance?
- Which districts show sustained improvement?
- What percentage of transit routes experienced delays?
- Which metrics are outside acceptable thresholds?
- What are the top operational KPIs today?
- Which systems exceeded historical baselines?
- What operational trends are accelerating?

**Semantic hints:** DAX measures on `CityPulseSnapshot`, `AnomalySignals`, PBIP semantic model.

---

## AI copilot

- Explain today's city conditions conversationally.
- What should city leadership pay attention to?
- Which systems need intervention right now?
- Describe operational health in simple language.
- Explain why the anomaly engine triggered alerts.
- What factors are driving operational stress?
- What should operations teams monitor tonight?
- Explain the current congestion pattern.
- Which signals indicate elevated disruption risk?
- What does the current City Stress Index mean?

**CLI:** `python -m pulsegrid.copilot.insights chicago --prompt "Explain today's city conditions"`

---

## Synthetic alerting

- Should the city issue a congestion advisory?
- Is operational stress above safe thresholds?
- Should airport operations escalate staffing?
- Are anomaly conditions severe enough for alerts?
- Which systems require immediate escalation?
- Is weather severity likely to impact mobility?
- Should transit systems enter high-alert mode?
- Are airport conditions approaching critical thresholds?
- Which districts require operational intervention?
- Should event traffic mitigation procedures activate?

**Semantic hints:** thresholds on `city_stress_index`, `AnomalySignals.severity`, `airport_ops_stress`, `Infrastructure Failure Risk`.

---

## ML classification

- Is this operational pattern anomalous?
- Classify current congestion severity.
- Determine whether airport operations are stable.
- Is the city currently in elevated stress mode?
- Does this event pattern indicate operational risk?
- Is the transit system operating normally?
- Does current weather increase disruption probability?
- Classify operational conditions by district.
- Is current activity density outside historical norms?
- Determine whether intervention is recommended.

**Labels:** see `training_labels` in `synthetic_questions.yaml`.

---

## Feature engineering

- Which variables contribute most to City Stress Index changes?
- Which metrics improve anomaly detection accuracy?
- What features best predict congestion spikes?
- Which external signals improve forecast quality?
- What geospatial features increase model performance?
- Which lag variables improve operational forecasting?
- What weather features correlate with mobility risk?
- Which event metrics predict transit instability?
- What derived metrics improve anomaly detection?
- Which operational indicators have strongest predictive power?

**Semantic hints:** `city_stress_index` components, `AnomalySignals.signal_type`, bronze feature tables.

---

## Advanced RAG / vector search

- Find historical scenarios similar to today's congestion pattern.
- Retrieve prior weather-related disruption events.
- Find past airport instability cases matching current conditions.
- Retrieve operational incidents similar to tonight's anomaly spike.
- Which historical events resemble current stress conditions?
- Find prior transit failures matching this pattern.
- Retrieve examples of cascading operational disruptions.
- Find similar event-driven congestion scenarios.
- Retrieve historical City Stress Index collapse events.
- Find operational recovery scenarios matching current conditions.

**Semantic hints:** embed `AnomalySignals.message`, `city_pulse_snapshot` history, bronze ingest narratives.

---

## Synthetic operational narratives

- Describe how severe weather disrupted city systems today.
- Explain the relationship between airport delays and congestion.
- Narrate today's operational timeline from morning to evening.
- Describe the chain reaction caused by transit failures.
- Explain how event density affected operational conditions.
- Describe how anomaly conditions propagated geographically.
- Narrate the operational recovery process.
- Explain current citywide mobility behavior.
- Describe how weather and events interacted operationally.
- Explain why the City Stress Index changed throughout the day.

---

## Suggested training labels

| Label | Source signal |
|-------|----------------|
| `pulse_score` | `city_stress_index` |
| `anomaly_detected` | any `AnomalySignals` row |
| `congestion_risk` | `transit_load_score` + `disruption_ratio_score` |
| `transit_failure_probability` | alert share + reroute signals |
| `airport_delay_risk` | `airport_ops_stress` |
| `operational_stress_level` | `city_stress_index` tiered |
| `mobility_instability` | `transit_load_score` |
| `event_disruption_score` | events + hex/event heat |
| `weather_impact_score` | `weather_risk_score`, NOAA counts |
| `escalation_required` | composite threshold breach |
| `infrastructure_failure_risk` | `InfrastructureRiskSnapshot` |
| `infrastructure_fatigue_risk` | road/bridge fatigue scores |

See also [`SYNTHETIC_QUESTIONS.md`](SYNTHETIC_QUESTIONS.md) for domain-specific sections (transit, weather, airport, infrastructure).

---

## Evaluation harness

```bash
python tools/run_synthetic_eval.py --category root_cause_analysis --city chicago --limit 5
python tools/run_synthetic_eval.py --category executive_summary --city chicago --out reports/synthetic-eval.md
```
