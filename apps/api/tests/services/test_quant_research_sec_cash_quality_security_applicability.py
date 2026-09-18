from datetime import UTC, date, datetime

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_security_applicability import ApplicabilityArtifactBindingV1, ApplicabilityLinkSessionBindingV1, SecCashQualitySecurityApplicabilityPlanV1
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import census_fingerprint
from tip_api.persistence.parquet.security_evidence import INSTRUMENT_EVIDENCE_SCHEMA
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import SELECTED_ENDPOINT_SCHEMA
from tip_api.persistence.quant_research_sec_cash_quality_security_applicability import publish_sec_cash_quality_security_applicability, read_sec_cash_quality_security_applicability
from tip_api.services.quant_research_sec_cash_quality_security_applicability import independently_verify_sec_cash_quality_security_applicability
from tip_api.services.quant_research_sec_cash_quality_ttm_coverage_v2 import TTM_V2_ARROW_SCHEMA
from tip_api.services.sec_filer_security_link_decision import LINK_ARROW_SCHEMA


def test_security_applicability_keeps_provider_form_non_effective_dated(tmp_path) -> None:
    session=date(2026,9,8); plan=_plan(session)
    result, verification=independently_verify_sec_cash_quality_security_applicability(
        ttm_rows=_ttm(),lineage_rows=_lineage(session),
        link_rows_by_session={session:_links(session, multi=False)},
        provider_form_rows=_provider(),
        session_opens={session:datetime(2026,9,8,13,30,tzinfo=UTC)},plan=plan,
    )
    assert result.identity_known_by_signal_open_count==1
    assert result.fully_applicable_endpoint_count==0
    assert dict(result.primary_blocker_counts)=={"security_form_not_effective_dated":1}
    assert dict(result.observed_provider_form_counts)=={"common_share":1}
    published=publish_sec_cash_quality_security_applicability(custody_root=tmp_path/'custody',plan=plan,result=result,verification=verification)
    assert read_sec_cash_quality_security_applicability(package_path=published.package_path).status=="exact_reread_complete"


def test_security_applicability_blocks_multiple_common_securities() -> None:
    session=date(2026,9,8); plan=_plan(session)
    result,_=independently_verify_sec_cash_quality_security_applicability(
        ttm_rows=_ttm(),lineage_rows=_lineage(session),
        link_rows_by_session={session:_links(session,multi=True)},
        provider_form_rows=_provider(),
        session_opens={session:datetime(2026,9,8,13,30,tzinfo=UTC)},plan=plan,
    )
    assert dict(result.primary_blocker_counts)=={"multiple_common_securities_for_cik":1}


def _plan(session):
    binding=ApplicabilityArtifactBindingV1(relative_path='x',physical_sha256='1'*64,byte_size=1,row_count=1)
    values={
        'ttm_verification_fingerprint':'2'*64,'ttm_result_fingerprint':'3'*64,'ttm_rows':binding,
        'lineage_selection_verification_fingerprint':'4'*64,'lineage_rows':binding,
        'link_manifest_logical_fingerprint':'5'*64,'link_manifest_physical_sha256':'6'*64,'link_manifest_byte_size':1,
        'link_sessions':(ApplicabilityLinkSessionBindingV1(session_date=session,relative_path='s',physical_sha256='7'*64,byte_size=1,row_count=1,point_in_time_eligibility='eligible_at_source_observed_at'),),
        'provider_form_manifest_physical_sha256':'8'*64,'provider_form_rows':binding,
        'calendar_version':'test','expected_ttm_endpoint_count':1,
    }
    p=SecCashQualitySecurityApplicabilityPlanV1.model_construct(**values,logical_fingerprint='0'*64)
    return SecCashQualitySecurityApplicabilityPlanV1.model_validate({**values,'logical_fingerprint':census_fingerprint(p)})


def _ttm():
    return pa.Table.from_pylist([{'companyfacts_cik':'0000000001','fiscal_year':2026,'fiscal_year_origin':date(2026,1,1),'fiscal_period':'Q2','period_end':date(2026,6,30),'ttm_cfo_text':'1','ttm_net_income_text':'1','opening_assets_text':'1','closing_assets_text':'1','average_assets_text':'1','knowledge_at_utc':datetime(2026,9,7,tzinfo=UTC),'component_accessions':['a'],'source_occurrence_ids':['a'*64]}],schema=TTM_V2_ARROW_SCHEMA)


def _lineage(session):
    rows=[]
    for q,c in (("assets_fiscal_boundary_v1","Assets"),("net_income_loss_fiscal_ytd_and_year_v1","NetIncomeLoss"),("operating_cash_flow_fiscal_ytd_and_year_v1","NetCashProvidedByUsedInOperatingActivities")):
        rows.append({'companyfacts_cik':'0000000001','fiscal_year':2026,'fiscal_year_origin':date(2026,1,1),'fiscal_period':'Q2','period_end':date(2026,6,30),'query_id':q,'concept_name':c,'value_kind':'integer','value_text':'1','accession_number':'a','source_available_at_utc':datetime(2026,9,7,tzinfo=UTC),'signal_eligible_session':session,'source_occurrence_ids':['a'*64]})
    return pa.Table.from_pylist(rows,schema=SELECTED_ENDPOINT_SCHEMA)


def _links(session,multi):
    rows=[]
    for i in range(2 if multi else 1):
        rows.append({'contract_version':'sec-filer-security-link-decision/1.0','as_of_date':session,'instrument_id':f'00000000-0000-0000-0000-{i+1:012d}','ticker':f'A{i}','instrument_type':'common_stock','sec_cik':'0000000001','sec_filer_key':'sec-cik:0000000001','decision_status':'admitted_unique_cik','reason_codes':[],'source_identity_occurrence_count':1,'cik_instrument_count':2 if multi else 1,'point_in_time_eligibility':'eligible_at_source_observed_at','source_observed_at':datetime(2026,9,8,12,tzinfo=UTC),'source_row_set_fingerprint':'9'*64,'issuer_projection_authorized':False})
    return pa.Table.from_pylist(rows,schema=LINK_ARROW_SCHEMA)


def _provider():
    return pa.Table.from_pylist([{'schema_version':'1.0','evidence_kind':'provider_security_type','evidence_version':'1','as_of_date':date(2026,8,14),'instrument_id':'00000000-0000-0000-0000-000000000001','provider':'massive_stocks_basic','provider_ticker':'A0','provider_type_code':'CS','provider_type_description':'Common','primary_exchange':'XNYS','provider_instrument_id':None,'cik':'0000000001','composite_figi':None,'share_class_figi':None,'security_form_evidence':'common_share','evidence_source':'provider','evidence_grade':'provider_explicit','classification_status':'resolved','universe_disposition':'quarantine','decision_flags':[],'review_flags':[],'provider_observation_ids':['a'*64],'observed_at':datetime(2026,8,16,tzinfo=UTC),'ingested_at':datetime(2026,8,16,tzinfo=UTC)}],schema=INSTRUMENT_EVIDENCE_SCHEMA)
