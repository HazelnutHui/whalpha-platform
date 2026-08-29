import { fetchJson } from './client';
import { parseReviewDeployment, type ReviewDeployment } from './reviewDeployment';

export interface PreviewUniverseDefinition {
  universe_id: string; display_name: string; catalog_order: number; is_default: boolean;
  member_count: number; membership_fingerprint: string;
}
export interface RegimeMetric {
  metric_id: string; lookback_sessions: number; raw_value: string | null; raw_unit: string;
  normalized_value: string | null; configured_weight: string; effective_weight: string;
  weighted_contribution: string | null; availability: string; missing_reason: string | null;
  reason_codes: string[];
}
export interface RegimeDimension {
  dimension_id: string; score: string | null; configured_weight: string; effective_weight: string;
  score_contribution: string | null; support_status: string; rendered_explanation: string;
  raw_metrics: RegimeMetric[]; reason_codes: string[];
}
export interface RegimeState {
  as_of_session?: string;
  composite: string | null; instantaneous_candidate_state: string | null; confirmed_state: string | null;
  transition_status: string; pending_target_state: string | null; confirmation_sessions_remaining: number;
  in_hysteresis_band: boolean; supporting_dimension_ids: string[]; conflicting_dimension_ids: string[];
  threshold_distances: Array<{ threshold_id: string; threshold: string; signed_distance: string; boundary_operator: string }>;
  reason_codes: string[];
}
export interface RegimeExplanation {
  candidate_band_text: string; transition_text: string; disclaimers: string[]; reason_codes: string[];
}
export interface UniverseAnalytics {
  definition: PreviewUniverseDefinition;
  composite: { regime_score: string | null; dimensions: RegimeDimension[]; reason_codes: string[]; logical_fingerprint: string };
  current_state: RegimeState;
  current_state_explanation: RegimeExplanation;
  state_history: RegimeState[];
  dimension_explanations: Array<{ subject_id: string; block_kind: string; rendered_text: string; reason_codes: string[] }>;
}
export interface RelationshipWindow {
  window_sessions: 5 | 10 | 20; start_session: string | null; end_session: string;
  left_return: string | null; right_return: string | null; relative_return: string | null;
  rolling_correlation: string | null; daily_return_observation_count: number; direction_combination: string | null;
  availability: string; missing_reason: string | null; reason_codes: string[];
}
export type LeadershipChange = 'strengthening' | 'weakening' | 'reversed' | 'new_leadership' | 'leadership_faded' | 'unchanged' | 'unavailable';
export interface RelationshipWindowChange {
  window_sessions: 5 | 10 | 20; current_relative_return: string | null;
  prior_1_session_relative_return: string | null; change_1_session: string | null;
  prior_5_session_relative_return: string | null; change_5_sessions: string | null;
  leadership_change_1: LeadershipChange; leadership_change_5: LeadershipChange;
}
export interface RelationshipChangeSummary {
  contract_version: 'relationship-change-summary/1.0'; pair_id: string; as_of_session: string;
  current_state_run_started_session: string; current_state_run_session_count: number;
  state_run_reaches_history_start: boolean; state_changed_this_session: boolean;
  current_5_session_leader: 'left' | 'right' | 'tied' | 'unavailable'; windows: RelationshipWindowChange[];
  reason_codes: string[]; disclaimer: 'descriptive_change_not_predictive_signal';
}
export interface RelationshipTimelinePoint {
  as_of_session: string; relationship_state: string; confidence: string;
  changed_from_prior_retained_session: boolean | null;
  windows: Array<{ window_sessions: 5 | 10 | 20; relative_return: string | null; availability: string }>;
}
export interface RelationshipStateTimeline {
  contract_version: 'relationship-state-timeline/1.0'; pair_id: string; as_of_session: string;
  retained_first_session: string; retained_session_count: number; displayed_session_count: number;
  truncated_before: boolean; points: RelationshipTimelinePoint[]; reason_codes: string[];
  disclaimer: 'descriptive_history_not_predictive_signal';
}
export interface Relationship {
  definition: { pair_id: string; registry_order: number; left_ticker: string; right_ticker: string;
    relationship_family: string; economic_rationale: string; expected_interpretation: string;
    forbidden_interpretation: string; availability_requirement: string };
  current: { relationship_state: string; confidence: string; availability: string; missing_reason: string | null;
    previous_relationship_state?: string | null;
    windows: RelationshipWindow[]; ratio_level: string | null; ratio_robust_z: string | null;
    ratio_percentile: string | null; correlation_20_prior_5: string | null; correlation_change_5: string | null;
    reason_codes: string[]; warnings: string[] };
  explanation: { left_observation: string; right_observation: string; relative_strength_observation: string;
    correlation_observation: string; cross_window_observation: string; supporting_evidence: string[];
    counterevidence: string[]; reason_codes: string[]; disclaimers: string[] };
  change_summary?: RelationshipChangeSummary;
  state_timeline?: RelationshipStateTimeline;
}
export interface RegimeRelationshipComparison { pair_id: string; alignment: string; reason_codes: string[] }
export interface MarketRegimePreviewResponse {
  schema_version: string; contract_version: string; bundle_logical_fingerprint: string;
  as_of_session: string; data_status: string; input_first_session: string; input_last_session: string;
  input_session_count: number; default_universe_id: string; selected_universe_id: string;
  available_universes: PreviewUniverseDefinition[]; source_logical_fingerprints: Record<string, string>;
  regime: UniverseAnalytics; relationships: Relationship[];
  relationship_comparisons: RegimeRelationshipComparison[]; warnings: string[];
  quality_gates: Array<{ gate_id: string; status: string; reason_codes: string[] }>;
  review_deployment?: ReviewDeployment | null;
}
const DECIMAL = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error(`Invalid Market Regime payload: ${label}`);
  return value as Record<string, unknown>;
}
function decimal(value: unknown, label: string): void {
  if (value !== null && (typeof value !== 'string' || !DECIMAL.test(value))) throw new Error(`Invalid Market Regime decimal: ${label}`);
}

export function parseMarketRegimePreview(value: unknown): MarketRegimePreviewResponse {
  const root = object(value, 'root');
  if (root.schema_version !== '1.0' || root.contract_version !== 'market-regime-opportunity-map-api/1.0') throw new Error('Unsupported Market Regime API contract');
  if (root.data_status === 'stale_review') {
    try { parseReviewDeployment(root.review_deployment, root.as_of_session); }
    catch { throw new Error('Invalid Market Regime review deployment contract'); }
  } else if (root.review_deployment !== null && root.review_deployment !== undefined) {
    throw new Error('Normal Market Regime response carries review metadata');
  }
  if (!Array.isArray(root.available_universes) || root.available_universes.length !== 2) throw new Error('Market Regime Universe catalog is incomplete');
  if (!Array.isArray(root.relationships) || root.relationships.length !== 16) throw new Error('Market Regime relationship registry is incomplete');
  const universes = root.available_universes.map((item) => object(item, 'Universe'));
  if (universes[0].is_default !== true || universes[0].universe_id !== root.default_universe_id) throw new Error('Market Regime default Universe is invalid');
  const pairIds = new Set<string>();
  root.relationships.forEach((item, pairIndex) => {
    const relationship = object(item, 'relationship'); const definition = object(relationship.definition, 'definition');
    const current = object(relationship.current, 'current'); const windows = current.windows;
    if (typeof definition.pair_id !== 'string' || pairIds.has(definition.pair_id)) throw new Error('Duplicate Market Regime pair');
    pairIds.add(definition.pair_id);
    if (definition.registry_order !== pairIndex || !Array.isArray(windows) || windows.length !== 3) throw new Error('Market Regime pair ordering is invalid');
    windows.forEach((window, index) => {
      const row = object(window, 'window'); if (row.window_sessions !== [5, 10, 20][index]) throw new Error('Market Regime window ordering is invalid');
      decimal(row.left_return, 'left_return'); decimal(row.right_return, 'right_return');
      decimal(row.relative_return, 'relative_return'); decimal(row.rolling_correlation, 'rolling_correlation');
    });
    if (relationship.change_summary !== undefined) {
      const summary = object(relationship.change_summary, 'relationship change summary');
      if (summary.contract_version !== 'relationship-change-summary/1.0'
        || summary.pair_id !== definition.pair_id || summary.as_of_session !== root.as_of_session
        || !Number.isInteger(summary.current_state_run_session_count)
        || Number(summary.current_state_run_session_count) < 1
        || typeof summary.state_run_reaches_history_start !== 'boolean'
        || typeof summary.state_changed_this_session !== 'boolean'
        || !['left', 'right', 'tied', 'unavailable'].includes(String(summary.current_5_session_leader))
        || summary.disclaimer !== 'descriptive_change_not_predictive_signal'
        || !Array.isArray(summary.windows) || summary.windows.length !== 3) {
        throw new Error('Market Regime relationship change summary is invalid');
      }
      summary.windows.forEach((change, index) => {
        const row = object(change, 'relationship window change');
        if (row.window_sessions !== [5, 10, 20][index]
          || !['strengthening', 'weakening', 'reversed', 'new_leadership', 'leadership_faded', 'unchanged', 'unavailable'].includes(String(row.leadership_change_1))
          || !['strengthening', 'weakening', 'reversed', 'new_leadership', 'leadership_faded', 'unchanged', 'unavailable'].includes(String(row.leadership_change_5))) {
          throw new Error('Market Regime relationship window change is invalid');
        }
        decimal(row.current_relative_return, 'current relative return');
        decimal(row.prior_1_session_relative_return, 'prior one-session relative return');
        decimal(row.change_1_session, 'one-session relationship change');
        decimal(row.prior_5_session_relative_return, 'prior five-session relative return');
        decimal(row.change_5_sessions, 'five-session relationship change');
      });
    }
    if (relationship.state_timeline !== undefined) {
      const timeline = object(relationship.state_timeline, 'relationship state timeline');
      const points = timeline.points;
      if (timeline.contract_version !== 'relationship-state-timeline/1.0'
        || timeline.pair_id !== definition.pair_id || timeline.as_of_session !== root.as_of_session
        || !Number.isInteger(timeline.retained_session_count) || Number(timeline.retained_session_count) < 1
        || !Number.isInteger(timeline.displayed_session_count) || Number(timeline.displayed_session_count) < 1
        || Number(timeline.displayed_session_count) > 10 || typeof timeline.truncated_before !== 'boolean'
        || typeof timeline.retained_first_session !== 'string' || !ISO_DATE.test(timeline.retained_first_session)
        || timeline.disclaimer !== 'descriptive_history_not_predictive_signal'
        || !Array.isArray(points) || points.length !== timeline.displayed_session_count
        || Number(timeline.retained_session_count) < points.length
        || timeline.truncated_before !== (Number(timeline.retained_session_count) > points.length)) {
        throw new Error('Market Regime relationship state timeline is invalid');
      }
      let priorSession = '';
      points.forEach((point, pointIndex) => {
        const row = object(point, 'relationship timeline point'); const pointWindows = row.windows;
        if (typeof row.as_of_session !== 'string' || !ISO_DATE.test(row.as_of_session) || row.as_of_session <= priorSession
          || !['relationship_break_candidate', 'rotation_candidate', 'divergence', 'synchronous_strengthening', 'synchronous_weakening', 'neutral', 'unavailable'].includes(String(row.relationship_state))
          || !['insufficient', 'low', 'medium', 'high'].includes(String(row.confidence))
          || (row.changed_from_prior_retained_session !== null && typeof row.changed_from_prior_retained_session !== 'boolean')
          || !Array.isArray(pointWindows) || pointWindows.length !== 3) {
          throw new Error('Market Regime relationship timeline point is invalid');
        }
        if (pointIndex === points.length - 1 && row.as_of_session !== root.as_of_session) {
          throw new Error('Market Regime relationship timeline is not current');
        }
        if (pointIndex === points.length - 1 && row.relationship_state !== current.relationship_state) {
          throw new Error('Market Regime relationship timeline current state differs');
        }
        if (pointIndex === 0) {
          if (timeline.truncated_before
            ? typeof row.changed_from_prior_retained_session !== 'boolean'
            : row.changed_from_prior_retained_session !== null) {
            throw new Error('Market Regime relationship timeline boundary is invalid');
          }
          if (timeline.truncated_before
            ? String(timeline.retained_first_session) >= row.as_of_session
            : String(timeline.retained_first_session) !== row.as_of_session) {
            throw new Error('Market Regime relationship retained boundary is invalid');
          }
        } else {
          const previousPoint = object(points[pointIndex - 1], 'prior relationship timeline point');
          if (row.changed_from_prior_retained_session
            !== (row.relationship_state !== previousPoint.relationship_state)) {
            throw new Error('Market Regime relationship timeline state-change marker differs');
          }
        }
        priorSession = row.as_of_session;
        pointWindows.forEach((timelineWindow, index) => {
          const windowRow = object(timelineWindow, 'relationship timeline window');
          if (windowRow.window_sessions !== [5, 10, 20][index]) {
            throw new Error('Market Regime relationship timeline window is invalid');
          }
          if (!['available', 'partial', 'unavailable'].includes(String(windowRow.availability))) {
            throw new Error('Market Regime relationship timeline availability is invalid');
          }
          decimal(windowRow.relative_return, 'timeline relative return');
        });
      });
    }
  });
  const regime = object(root.regime, 'regime'); const composite = object(regime.composite, 'composite');
  decimal(composite.regime_score, 'regime_score');
  if (!Array.isArray(composite.dimensions) || composite.dimensions.length !== 5) throw new Error('Market Regime dimension ledger is incomplete');
  composite.dimensions.forEach((item) => {
    const dimension = object(item, 'dimension'); decimal(dimension.score, 'dimension score'); decimal(dimension.score_contribution, 'dimension contribution');
  });
  return value as MarketRegimePreviewResponse;
}

export async function getMarketRegimePreview(universeId: string | undefined, signal?: AbortSignal): Promise<MarketRegimePreviewResponse> {
  if (import.meta.env.VITE_MARKET_DATA_MODE === 'snapshot') {
    const envelope = object(
      await fetchJson<unknown>('/private-data/v1/market-regime-overviews.json', signal),
      'snapshot envelope',
    );
    if (
      envelope.schema_version !== '1.0'
      || envelope.contract_version !== 'market-regime-snapshot/1.0'
      || !Array.isArray(envelope.records)
      || envelope.records.length !== 2
      || !Array.isArray(envelope.universe_order)
      || envelope.universe_order.length !== 2
    ) throw new Error('Unsupported Market Regime snapshot contract');
    const selected = universeId ?? envelope.default_universe_id;
    const record = envelope.records.find((item) => object(item, 'snapshot record').selected_universe_id === selected);
    if (!record) throw new Error('Selected Market Regime Universe is unavailable');
    return parseMarketRegimePreview(record);
  }
  const query = universeId ? `?universe_id=${encodeURIComponent(universeId)}` : '';
  return parseMarketRegimePreview(await fetchJson<unknown>(`/api/v1/private/market-regime/overview${query}`, signal));
}
