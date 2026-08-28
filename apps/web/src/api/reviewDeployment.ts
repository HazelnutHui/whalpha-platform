export type ReviewDeploymentContractVersion =
  | 'production-review-deployment/1.0'
  | 'production-review-deployment/1.1';

export interface ReviewDeployment {
  contract_version: ReviewDeploymentContractVersion;
  review_mode: true;
  normal_freshness: false;
  data_status: 'stale_review';
  approved_as_of_session: string;
  expected_latest_session: string;
  expected_lag_sessions: 1;
  explicit_user_acknowledgement: string;
}

const BINDINGS: Record<ReviewDeploymentContractVersion, {
  approved: string; expected: string; acknowledgement: string;
}> = {
  'production-review-deployment/1.0': {
    approved: '2026-08-24', expected: '2026-08-25',
    acknowledgement: 'I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1',
  },
  'production-review-deployment/1.1': {
    approved: '2026-08-26', expected: '2026-08-27',
    acknowledgement: 'I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1',
  },
};

export function reviewMetadataMatches(
  contract: unknown, approved: unknown, expected: unknown, lag: unknown,
): boolean {
  if (typeof contract !== 'string' || !(contract in BINDINGS)) return false;
  const binding = BINDINGS[contract as ReviewDeploymentContractVersion];
  return approved === binding.approved && expected === binding.expected && lag === 1;
}

export function parseReviewDeployment(value: unknown, asOfSession: unknown): ReviewDeployment {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error('Invalid review deployment contract');
  }
  const review = value as Record<string, unknown>;
  if (!reviewMetadataMatches(
    review.contract_version, review.approved_as_of_session,
    review.expected_latest_session, review.expected_lag_sessions,
  )) throw new Error('Invalid review deployment contract');
  const binding = BINDINGS[review.contract_version as ReviewDeploymentContractVersion];
  if (review.review_mode !== true || review.normal_freshness !== false
    || review.data_status !== 'stale_review'
    || review.approved_as_of_session !== asOfSession
    || review.explicit_user_acknowledgement !== binding.acknowledgement) {
    throw new Error('Invalid review deployment contract');
  }
  return review as unknown as ReviewDeployment;
}
