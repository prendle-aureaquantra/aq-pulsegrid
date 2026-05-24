# AQ PulseGrid — Synthetic Questions (AI / ML / Semantic Layer)

These questions simulate executive prompts, operational analytics, anomaly detection, forecasting, semantic BI querying, and AI copilot interactions.

**Use for:** synthetic QA pairs, evaluation prompts, semantic layer test cases, dashboard narratives, copilot demos, RAG/vector search examples.

**Expanded ML / RAG training set (v2):** [`SYNTHETIC_MODEL_TRAINING_QUESTIONS.md`](SYNTHETIC_MODEL_TRAINING_QUESTIONS.md) — root cause, comparative, temporal, predictive, correlation, alerting, classification, feature engineering, narratives (~170 prompts).

**Platform report:** filter by `DimMetro[metro_label]` on the PulseGrid PBIP; per-city reports use `CityPulseSnapshot`, `TransitAlertSummary`, `AnomalySignals`, etc.

**Terminology (current model):**

| Legacy / colloquial | Semantic model |
|---------------------|----------------|
| Pulse Score | **City Stress Index** (`city_stress_index`, 0–100) |
| CTA delays / alerts | **Active Transit Alerts** (`active_transit_alerts`) + `TransitAlertSummary` |
| NOAA / weather alerts | **Active NOAA Alerts** (`active_noaa_alerts`) |
| Anomaly score | **AnomalySignals** (`signal_type`, `z_score`, `severity`) |

---

## Executive intelligence

- Why is the Chicago City Stress Index down today?
- Which city has the highest operational stress right now?
- What factors contributed most to today’s congestion increase?
- Which metro areas show the largest activity spike this week?
- What are the top operational risks currently affecting Chicago?
- Which signals are most volatile today?
- What events are driving increased downtown activity?
- What regions are showing abnormal behavior?
- Which operational systems are under the most stress?
- Which city has the highest anomaly count?

**Semantic hints:** `CityPulseSnapshot`, `AnomalySignals`, `DimMetro`, measures `City Stress Index`, `Anomaly Count`.

---

## Transit & mobility

- Which transit alert categories spiked today?
- Are transit disruptions correlated with weather events?
- Which neighborhoods experienced the largest congestion spikes?
- What time of day has the highest transit disruption rate?
- Which areas show recurring operational anomalies on the hex grid?
- Which routes or alert types are most impacted during large events?
- Are transit alerts increasing compared to last week?
- Which transit incidents had the largest citywide impact?
- Which mobility signals predict stress index increases?
- Which areas show unusual alert density on `HexPulseGrid`?

**Semantic hints:** `TransitAlertSummary[alert_category, alert_count]`, `active_transit_alerts`, `HexPulseGrid`, `transit_load_score`.

---

## Weather intelligence

- How did severe weather impact city operations?
- Which weather conditions correlate most strongly with transit alerts?
- Did rainfall affect forecast precipitation risk scores?
- Which regions experienced the highest weather-related disruption?
- Are airport METAR categories degrading during temperature swings?
- Which weather events caused the largest anomaly spikes?
- What operational systems are most weather-sensitive?
- How does air quality relate to city stress (where AQI bronze exists)?
- Which forecast periods drive `precip_risk_score`?
- Which events were impacted by storm or MeteoAlarm activity?

**Semantic hints:** `weather_risk_score`, `precip_risk_score`, `active_noaa_alerts`, `WeatherForecastPeriods`.

---

## Airport & aviation

- Which airport has the highest ops stress today?
- Are airport METAR categories affecting regional stress scores?
- Which stations show the worst flight category?
- What time periods show the highest aviation-related stress?
- Are airport issues correlated with weather anomalies?
- Which airports have recurring operational instability?
- How do airport delays relate to city stress components?
- Which regions are impacted most by aviation disruptions?
- Which METAR fields drive `airport_ops_stress`?
- Are airport stress scores increasing week-over-week?

**Semantic hints:** `AirportOpsSnapshot`, `flight_category`, `visibility_sm`, `airport_ops_stress`.

---

## Infrastructure (roads, bridges, fatigue & failure risk)

- Which metros show the highest bridge or structural failure risk?
- Are open pothole and pavement requests driving fatigue risk this week?
- How many critical open infrastructure 311 requests are there in Chicago?
- Drill from asset class to risk tier to individual service requests.
- Does precipitation correlate with road surface fatigue scores?
- Which asset classes (bridge, road surface, structural) dominate open requests?
- What is the difference between failure risk and fatigue risk on the dashboard?
- Are bridge-related 311 descriptors increasing compared to last snapshot?

**Semantic hints:** `InfrastructureRiskSnapshot`, `InfrastructureAssetSummary`, `InfrastructureRequestDetail`, measures `Infrastructure Failure Risk`, `Infrastructure Fatigue Risk`, `Bridge Risk Score`, `open_infrastructure_requests`. Data source: civic 311 (Chicago, NYC, LA, SF, Boston, DC).

---

## Event intelligence

- Which events are generating the largest activity spikes?
- Are large events associated with higher transit alert volume?
- Which sports or concert patterns impact downtown operations most?
- Which neighborhoods show event-driven hex anomalies?
- What event types correlate with trends interest surges?
- Which venues generate the highest mobility impact?
- How do festivals affect City Stress Index?
- Which events coincide with airport stress increases?
- What event signals correlate with weather-related disruptions?
- Which upcoming events may create operational risk?

**Semantic hints:** events bronze → silver (city-dependent), `TrendInterestSummary`, `HexPulseGrid`.

---

## Anomaly detection

- Which operational signals are behaving abnormally?
- What caused the largest anomaly today?
- Which neighborhoods show unexpected activity patterns?
- Which metrics exceeded historical thresholds?
- Are transit anomalies increasing?
- Which weather conditions triggered anomaly alerts?
- Which systems generated repeated anomaly scores?
- Which regions show unusual congestion patterns?
- Which airport metrics are outside normal ranges?
- What are the top anomaly contributors this week?

**Semantic hints:** `AnomalySignals` (`transit_alert_spike`, `weather_alert_spike`, `precip_forecast_spike`, `reroute_share_spike`).

---

## Forecasting (aspirational / ML roadmap)

- Predict tomorrow’s Chicago City Stress Index.
- Which city is likely to experience elevated stress tomorrow?
- Forecast transit alert volume for the next 24 hours.
- Predict airport disruption severity for the weekend.
- Which regions are at highest risk for operational instability?
- Forecast event-driven congestion increases.
- Which neighborhoods are likely to experience mobility spikes?
- Predict severe weather operational impacts.
- Forecast anomaly probability by district.
- Which metrics are expected to trend upward this week?

**Note:** Production pipeline today is snapshot + z-score anomalies, not trained forecasts. Use for ML backlog and copilot “what-if” demos.

---

## Geospatial intelligence

- Which neighborhoods are operational hotspots?
- Where are anomaly clusters concentrated?
- Which districts have the highest alert density?
- Which regions show elevated stress patterns?
- Where are airport impacts spreading geographically?
- Which areas have the highest event density?
- Which neighborhoods are most transit-dependent?
- Which areas show unusual mobility behavior on the hex grid?
- What regions correlate most strongly with weather disruption?
- Which districts are operationally stable?

**Semantic hints:** `HexPulseGrid[neighborhood, alert_count]`, `neighborhood_hint` on transit alerts (Chicago keyword enrichment).

---

## AI copilot / semantic layer

- Summarize today’s operational risks.
- Explain why the City Stress Index decreased.
- Which systems contributed most to congestion?
- What are the top operational insights today?
- Describe current citywide anomalies.
- Explain transit disruptions in plain English.
- Summarize airport operations today.
- Which signals require immediate attention?
- Generate an executive operations briefing.
- Explain current operational conditions for non-technical leadership.

**CLI:** `python -m pulsegrid.copilot.insights chicago --prompt "Summarize today's operational risks"`

---

## PBIP / dashboard demo

- Generate a dashboard for Chicago operations.
- Build a transit operations report.
- Generate anomaly detection visuals.
- Create an executive City Stress Index dashboard.
- Build an airport disruption analysis page.
- Generate weather impact visuals.
- Create geospatial congestion heatmaps.
- Generate semantic KPI pages.
- Build a citywide operations summary report.
- Generate operational trend dashboards.

**Implementation:** `python generate_city.py --city chicago --with-visuals` or `--platform-only --with-visuals` for worldwide `PulseGrid.pbip`.

---

## ML training labels

Canonical list in `synthetic_questions.yaml` → `training_labels`:

| Label | Source signal |
|-------|----------------|
| `pulse_score` | `city_stress_index` |
| `anomaly_detected` | `AnomalySignals` any row |
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

---

## Example synthetic training record

```json
{
  "city": "chicago",
  "snapshot_at": "2026-05-24T18:30:00+00:00",
  "city_stress_index": 82.4,
  "transit_load_score": 28.0,
  "weather_risk_score": 12.0,
  "precip_risk_score": 8.5,
  "disruption_ratio_score": 6.2,
  "active_transit_alerts": 123,
  "active_noaa_alerts": 2,
  "avg_precip_pct_next_periods": 45.0,
  "anomaly_detected": true,
  "signal_types": ["transit_alert_spike"]
}
```

---

## Suggested AI use cases

- Anomaly detection (live: z-score vs baselines / history)
- Operational summarization (`pulsegrid.copilot.insights`)
- Semantic search over `semantic_model_metadata.json` + gold tables
- RAG over bronze ingest paths and anomaly messages
- Executive copilots (platform slicer + narrative)
- Vector embeddings of `AnomalySignals.message` (future)
- Dashboard narration for PBIP pages
- KPI explanation grounded in DAX measures
- Intelligent alerting (Slack webhook in `.env`)

---

## Recommended expansion

- LLM operational copilot with tool calls to Delta / PBIP
- Vector search over historical `city_pulse_snapshot`
- Natural-language-to-DAX (semantic layer aware)
- AI-generated executive briefings per metro
- Autonomous anomaly digests
- Predictive city stress (time-series model on `pulse_history`)

---

## Evaluation harness

Machine-readable list: [`datasets/reference/synthetic_questions.yaml`](../datasets/reference/synthetic_questions.yaml)

```bash
# Run copilot against a category (requires OPENAI_API_KEY)
python tools/run_synthetic_eval.py --category executive --city chicago --limit 3
python tools/run_synthetic_eval.py --category root_cause_analysis --city chicago --limit 5
python tools/run_synthetic_eval.py --category operational_narratives --city chicago --out reports/synthetic-eval.md
```

List categories: `python -c "import yaml; print('\\n'.join(yaml.safe_load(open('datasets/reference/synthetic_questions.yaml'))['categories']))"`
