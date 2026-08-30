import { fetchJson } from './client';
import { parseSnapshotManifest } from './market';

export type SectorRotationPosture =
  | 'leading_improving'
  | 'leading_weakening'
  | 'lagging_improving'
  | 'lagging_weakening'
  | 'neutral'
  | 'unavailable';

export interface SectorRotationWindow {
  window_sessions: 5 | 10 | 20;
  start_session: string | null;
  end_session: string;
  etf_return: string | null;
  spy_return: string | null;
  relative_return: string | null;
  relative_rank: number | null;
  available_peer_count: number;
  availability: 'available' | 'unavailable';
  missing_reason: string | null;
}

export interface SectorRotationRecord {
  ticker: string;
  sector: string;
  registry_order: number;
  as_of_session: string;
  windows: [SectorRotationWindow, SectorRotationWindow, SectorRotationWindow];
  five_day_relative_acceleration: string | null;
  posture: SectorRotationPosture;
  five_day_leadership_run_sessions: number;
  run_reaches_history_start: boolean;
  availability: 'available' | 'unavailable';
  missing_reason: string | null;
  supporting_fact_codes: string[];
  counterevidence_codes: string[];
  warnings: string[];
  logical_fingerprint: string;
}

export interface SectorRotationResponse {
  publication_id: string;
  payload_sha256: string;
  payload_logical_fingerprint: string;
  audit_logical_fingerprint: string;
  parameter_fingerprint: string;
  history_source_fingerprint: string;
  product_logical_fingerprint: string;
  snapshot_logical_fingerprint: string;
  as_of_session: string;
  input_session_count: number;
  records: SectorRotationRecord[];
  warnings: string[];
  theme_status: 'unavailable_no_governed_membership';
}

const TICKERS = ['XLC', 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLK', 'XLU'];
const POSTURES: SectorRotationPosture[] = [
  'leading_improving', 'leading_weakening', 'lagging_improving',
  'lagging_weakening', 'neutral', 'unavailable',
];

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return value as Record<string, unknown>;
}
function string(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return value;
}
function nullableString(value: unknown, label: string): string | null {
  return value === null ? null : string(value, label);
}
function integer(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return value;
}
function boolean(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return value;
}
function strings(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return value;
}
function digest(value: unknown, label: string): string {
  const result = string(value, label);
  if (!/^[0-9a-f]{64}$/.test(result)) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return result;
}
function decimal(value: unknown, label: string): string | null {
  const result = nullableString(value, label);
  if (result !== null && !Number.isFinite(Number(result))) throw new Error(`Invalid Sector Rotation payload: ${label}`);
  return result;
}

function parseWindow(value: unknown, expectedWindow: 5 | 10 | 20): SectorRotationWindow {
  const row = record(value, `${expectedWindow}-session window`);
  const availability = string(row.availability, 'window availability');
  const relativeRank = row.relative_rank === null ? null : integer(row.relative_rank, 'relative rank');
  const result: SectorRotationWindow = {
    window_sessions: integer(row.window_sessions, 'window sessions') as 5 | 10 | 20,
    start_session: nullableString(row.start_session, 'start session'),
    end_session: string(row.end_session, 'end session'),
    etf_return: decimal(row.etf_return, 'ETF return'),
    spy_return: decimal(row.spy_return, 'SPY return'),
    relative_return: decimal(row.relative_return, 'relative return'),
    relative_rank: relativeRank,
    available_peer_count: integer(row.available_peer_count, 'peer count'),
    availability: availability as SectorRotationWindow['availability'],
    missing_reason: nullableString(row.missing_reason, 'window missing reason'),
  };
  if (result.window_sessions !== expectedWindow || !['available', 'unavailable'].includes(availability)) throw new Error('Sector Rotation window registry differs');
  if (availability === 'available' && (result.start_session === null || result.relative_return === null || relativeRank === null || relativeRank < 1 || relativeRank > result.available_peer_count)) throw new Error('Sector Rotation available window is incomplete');
  if (availability === 'unavailable' && (result.relative_return !== null || relativeRank !== null || result.missing_reason === null)) throw new Error('Sector Rotation unavailable window is inconsistent');
  return result;
}

function parseRotationRecord(value: unknown, expectedTicker: string, index: number, session: string): SectorRotationRecord {
  const row = record(value, `record ${index}`);
  if (!Array.isArray(row.windows) || row.windows.length !== 3) throw new Error('Sector Rotation windows are incomplete');
  const posture = string(row.posture, 'posture') as SectorRotationPosture;
  const availability = string(row.availability, 'record availability') as SectorRotationRecord['availability'];
  const result: SectorRotationRecord = {
    ticker: string(row.ticker, 'ticker'), sector: string(row.sector, 'sector'),
    registry_order: integer(row.registry_order, 'registry order'), as_of_session: string(row.as_of_session, 'record session'),
    windows: [parseWindow(row.windows[0], 5), parseWindow(row.windows[1], 10), parseWindow(row.windows[2], 20)],
    five_day_relative_acceleration: decimal(row.five_day_relative_acceleration, 'relative acceleration'),
    posture, five_day_leadership_run_sessions: integer(row.five_day_leadership_run_sessions, 'leadership run'),
    run_reaches_history_start: boolean(row.run_reaches_history_start, 'run truncation'), availability,
    missing_reason: nullableString(row.missing_reason, 'record missing reason'),
    supporting_fact_codes: strings(row.supporting_fact_codes, 'supporting facts'),
    counterevidence_codes: strings(row.counterevidence_codes, 'counterevidence'),
    warnings: strings(row.warnings, 'warnings'), logical_fingerprint: digest(row.logical_fingerprint, 'record fingerprint'),
  };
  if (result.ticker !== expectedTicker || result.registry_order !== index || result.as_of_session !== session
    || !POSTURES.includes(posture) || !['available', 'unavailable'].includes(availability)) throw new Error('Sector Rotation record registry differs');
  return result;
}

export function parseSectorRotation(value: unknown): SectorRotationResponse {
  const envelope = record(value, 'envelope');
  const source = record(envelope.source, 'source');
  const product = record(envelope.product, 'product');
  if (envelope.schema_version !== '1.0' || envelope.contract_version !== 'sector-etf-rotation-dashboard-snapshot/1.0'
    || envelope.market_intelligence_contract_version !== 'market-intelligence-publication/1.3'
    || envelope.language_neutral !== true || envelope.fixed_sector_etf_proxy_only !== true
    || envelope.constituent_breadth_unavailable !== true || envelope.fund_flow_claim_prohibited !== true
    || envelope.theme_membership_unavailable !== true || envelope.guest_and_credential_capability_identical !== true
    || source.audit_contract_version !== 'sector-etf-rotation-audit/1.0'
    || source.product_contract_version !== 'sector-etf-rotation/1.0'
    || source.calculation_version !== 'sector-etf-rotation-v1.0.0'
    || source.oracle_mismatch_count !== 0 || source.record_count !== 11
    || product.schema_version !== '1.0' || product.contract_version !== 'sector-etf-rotation/1.0'
    || product.calculation_version !== 'sector-etf-rotation-v1.0.0' || product.benchmark_ticker !== 'SPY'
    || product.theme_status !== 'unavailable_no_governed_membership' || !Array.isArray(product.records)
    || product.records.length !== 11) throw new Error('Unsupported Sector Rotation snapshot');
  const session = string(product.as_of_session, 'as-of session');
  const productFingerprint = digest(product.logical_fingerprint, 'product fingerprint');
  const parameterFingerprint = digest(product.parameter_fingerprint, 'parameter fingerprint');
  const historyFingerprint = digest(product.source_history_fingerprint, 'history fingerprint');
  const records = product.records.map((item, index) => parseRotationRecord(item, TICKERS[index], index, session));
  if (source.product_logical_fingerprint !== productFingerprint || source.parameter_fingerprint !== parameterFingerprint
    || source.history_source_fingerprint !== historyFingerprint || source.theme_status !== product.theme_status) throw new Error('Sector Rotation source binding differs');
  return {
    publication_id: string(envelope.publication_id, 'publication id'),
    payload_sha256: digest(envelope.payload_sha256, 'payload SHA'),
    payload_logical_fingerprint: digest(envelope.payload_logical_fingerprint, 'payload fingerprint'),
    audit_logical_fingerprint: digest(source.audit_logical_fingerprint, 'audit fingerprint'),
    parameter_fingerprint: parameterFingerprint, history_source_fingerprint: historyFingerprint,
    product_logical_fingerprint: productFingerprint,
    snapshot_logical_fingerprint: digest(envelope.logical_fingerprint, 'snapshot fingerprint'),
    as_of_session: session, input_session_count: integer(product.input_session_count, 'input sessions'),
    records, warnings: strings(product.warnings, 'warnings'),
    theme_status: product.theme_status as SectorRotationResponse['theme_status'],
  };
}

export async function getSectorRotation(signal?: AbortSignal): Promise<SectorRotationResponse> {
  const manifest = parseSnapshotManifest(await fetchJson<unknown>('/private-data/v1/manifest.json', signal));
  if (manifest.snapshot_contract_version !== '1.11' || manifest.dashboard_contract_version !== '2.8'
    || manifest.sector_rotation_file !== 'sector-etf-rotation.json') throw new Error('Sector Rotation snapshot is unavailable');
  const parsed = parseSectorRotation(await fetchJson<unknown>(`/private-data/v1/${manifest.sector_rotation_file}`, signal));
  if (parsed.publication_id !== manifest.market_intelligence_publication_id
    || parsed.payload_sha256 !== manifest.market_intelligence_payload_sha256
    || parsed.payload_logical_fingerprint !== manifest.market_intelligence_logical_fingerprint
    || parsed.snapshot_logical_fingerprint !== manifest.sector_rotation_snapshot_logical_fingerprint
    || parsed.audit_logical_fingerprint !== manifest.sector_rotation_audit_logical_fingerprint
    || parsed.parameter_fingerprint !== manifest.sector_rotation_parameter_fingerprint
    || parsed.history_source_fingerprint !== manifest.sector_rotation_history_source_fingerprint
    || parsed.product_logical_fingerprint !== manifest.sector_rotation_product_logical_fingerprint
    || parsed.as_of_session !== manifest.current_session_date) throw new Error('Sector Rotation manifest binding differs');
  return parsed;
}
