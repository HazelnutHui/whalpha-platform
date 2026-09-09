import type { MarketRegimePreviewResponse } from '../api/marketRegime';
import type { CandidateListItem, OpportunityCandidateResponse } from '../api/opportunityCandidates';
import type { SectorRotationRecord, SectorRotationResponse } from '../api/sectorRotation';

export type DecisionChainWindow = 5 | 10 | 20;

export interface RankedCandidateSummary {
  item: CandidateListItem;
  balanced_rank: number;
}

export interface MarketDecisionChain {
  as_of_session: string;
  universe_id: string;
  confirmed_market_state: string | null;
  regime_score: string | null;
  sector_proxies: SectorRotationRecord[];
  candidates: RankedCandidateSummary[];
  balanced_display_count: number;
}

const DEFAULT_SECTOR_COUNT = 5;
const DEFAULT_CANDIDATE_COUNT = 8;

function windowIndex(window: DecisionChainWindow): number {
  return window === 5 ? 0 : window === 10 ? 1 : 2;
}

export function buildMarketDecisionChain(
  regime: MarketRegimePreviewResponse,
  rotation: SectorRotationResponse,
  candidateResponse: OpportunityCandidateResponse,
  window: DecisionChainWindow,
): MarketDecisionChain {
  if (regime.as_of_session !== rotation.as_of_session
    || candidateResponse.as_of_session !== rotation.as_of_session) {
    throw new Error('Decision-chain sessions differ');
  }
  if (candidateResponse.publication_id !== rotation.publication_id) {
    throw new Error('Decision-chain publications differ');
  }
  if (regime.selected_universe_id !== candidateResponse.selected_universe_id
    || candidateResponse.selected_universe_id !== candidateResponse.universe.universe_id) {
    throw new Error('Decision-chain Universes differ');
  }

  const index = windowIndex(window);
  const sectorProxies = [...rotation.records]
    .filter((item) => item.windows[index].availability === 'available')
    .sort((left, right) => {
      const leftRank = left.windows[index].relative_rank ?? Number.MAX_SAFE_INTEGER;
      const rightRank = right.windows[index].relative_rank ?? Number.MAX_SAFE_INTEGER;
      return leftRank - rightRank || left.registry_order - right.registry_order;
    })
    .slice(0, DEFAULT_SECTOR_COUNT);

  const balanced = candidateResponse.universe.risk_modes.find((item) => item.risk_mode === 'balanced');
  if (!balanced) throw new Error('Decision-chain balanced Candidate view is unavailable');
  const byId = new Map(candidateResponse.universe.candidates.map((item) => [item.instrument_id, item]));
  const candidates = balanced.displayed_instrument_ids.slice(0, DEFAULT_CANDIDATE_COUNT).map((instrumentId, candidateIndex) => {
    const item = byId.get(instrumentId);
    if (!item) throw new Error('Decision-chain Candidate summary is incomplete');
    return { item, balanced_rank: candidateIndex + 1 };
  });

  return {
    as_of_session: rotation.as_of_session,
    universe_id: candidateResponse.selected_universe_id,
    confirmed_market_state: regime.regime.current_state.confirmed_state,
    regime_score: regime.regime.composite.regime_score,
    sector_proxies: sectorProxies,
    candidates,
    balanced_display_count: balanced.displayed_instrument_ids.length,
  };
}
