from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationRecordV1, SecurityTypeCountV1
from tip_api.persistence.parquet import dashboard_universe_activation as repo
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID
from tip_api.services.provider_classified_universe import CANDIDATE_B_ID
from tip_api.services.universe_pre_activation import membership_fingerprint
from tip_api.services import dashboard_universe_activation_cli as cli

SESSION=date(2026,8,19); AT=datetime(2026,8,20,tzinfo=UTC); SHA="a"*64
IDS=(UUID("00000000-0000-5000-8000-500000000001"),UUID("00000000-0000-5000-8000-500000000002"),UUID("00000000-0000-5000-8000-500000000003"))

def records():
    common=frozenset(IDS[:2]); broad=frozenset(IDS)
    def item(n,uid,members,name,composition,default):
        return DashboardUniverseActivationRecordV1(activation_id=UUID(uid),analysis_session=SESSION,membership_evidence_as_of=date(2026,8,14),activated_at=AT,universe_id=n,display_name=name,long_display_name=name,description="fixture",is_default=default,member_count=len(members),security_type_composition=tuple(SecurityTypeCountV1(provider_type_code=k,count=v) for k,v in composition.items()),membership_fingerprint=membership_fingerprint(members),trailing_liquidity_source_fingerprint=SHA,reviewed_override_source_fingerprint=SHA,pre_activation_review_fingerprint=SHA,current_eod_fingerprint=SHA,previous_eod_fingerprint=SHA,legacy_rollback_reference="market-data/snapshots/legacy",limitations=("fixture",))
    return (item(CANDIDATE_A_ID,"00000000-0000-5000-8000-500000000010",common,"Common Shares",{"CS":2},True),item(repo.PUBLIC_SECONDARY_ID,"00000000-0000-5000-8000-500000000011",broad,"Common Shares + ADRs",{"CS":2,"ADRC":1},False)),{CANDIDATE_A_ID:common,repo.PUBLIC_SECONDARY_ID:broad}

def fake_sources(monkeypatch,members):
    review=SimpleNamespace(manifest=SimpleNamespace(logical_content_fingerprint=SHA,legacy_count=3,legacy_membership_fingerprint=SHA,review_dataset=SimpleNamespace(dataset_path="fixture"),override_dataset=SimpleNamespace(record_count=2)))
    monkeypatch.setattr(repo,"read_completed_universe_review",lambda *a,**k:review)
    source={CANDIDATE_A_ID:members[CANDIDATE_A_ID],CANDIDATE_B_ID:members[repo.PUBLIC_SECONDARY_ID]}
    monkeypatch.setattr(repo,"_read_review_members",lambda *a,**k:source)

def test_contract_rejects_bad_composition():
    values,_=records()
    payload=values[0].model_dump();payload["member_count"]=3
    with pytest.raises(ValueError): DashboardUniverseActivationRecordV1.model_validate(payload)

def test_atomic_publication_and_final_formal_reread_exit_path(tmp_path,monkeypatch):
    values,members=records(); fake_sources(monkeypatch,members)
    result=repo.ParquetDashboardUniverseActivationRepository(tmp_path).publish(records=values,legacy_count=3,legacy_fingerprint=SHA,trailing_window_start=date(2026,7,22),trailing_window_end=date(2026,8,18),trailing_window_session_count=20,reviewed_override_count=2,activated_at=AT)
    assert result.record_count==2
    completed=repo.read_completed_dashboard_universe_activation(tmp_path,analysis_session=SESSION,validate_sources=True)
    assert completed.select(None)[0].universe_id==CANDIDATE_A_ID
    assert completed.select(repo.PUBLIC_SECONDARY_ID)[1]==members[repo.PUBLIC_SECONDARY_ID]
    assert not tuple(tmp_path.rglob("*staging*"))

def test_existing_target_and_unknown_universe_fail_closed(tmp_path,monkeypatch):
    values,members=records(); fake_sources(monkeypatch,members)
    publisher=repo.ParquetDashboardUniverseActivationRepository(tmp_path)
    publisher.publish(records=values,legacy_count=3,legacy_fingerprint=SHA,trailing_window_start=date(2026,7,22),trailing_window_end=date(2026,8,18),trailing_window_session_count=20,reviewed_override_count=2,activated_at=AT)
    with pytest.raises(repo.DashboardUniverseActivationConflictError): publisher.publish(records=values,legacy_count=3,legacy_fingerprint=SHA,trailing_window_start=date(2026,7,22),trailing_window_end=date(2026,8,18),trailing_window_session_count=20,reviewed_override_count=2,activated_at=AT)
    completed=repo.read_completed_dashboard_universe_activation(tmp_path,analysis_session=SESSION)
    with pytest.raises(ValueError): completed.select("../../etc/passwd")

def test_symlink_root_rejected(tmp_path):
    target=tmp_path/"target";target.mkdir();link=tmp_path/"link";link.symlink_to(target,target_is_directory=True)
    with pytest.raises(repo.DashboardUniverseActivationError): repo.read_completed_dashboard_universe_activation(link,analysis_session=SESSION)

def test_cli_apply_returns_zero_after_final_formal_reread(monkeypatch, capsys):
    values,_=records()
    inputs=cli.ActivationInputs(values,3,SHA,date(2026,7,22),date(2026,8,18),20,2,AT)
    published=SimpleNamespace(content_fingerprint=SHA,parquet_sha256=SHA,logical_content_fingerprint=SHA)
    publisher=SimpleNamespace(publish=lambda **kwargs: published)
    monkeypatch.setattr(cli,"_prepare_inputs",lambda: inputs)
    monkeypatch.setattr(cli,"ParquetDashboardUniverseActivationRepository",lambda root: publisher)
    monkeypatch.setattr(cli,"read_completed_dashboard_universe_activation",lambda *args,**kwargs: SimpleNamespace(universes=values))
    assert cli.main(["--apply"])==0
    assert '"status": "completed"' in capsys.readouterr().out
