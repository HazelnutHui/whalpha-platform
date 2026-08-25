"""Offline, tmp-only Phase 2 ETF relationship replay CLI."""

from __future__ import annotations

import argparse
import json
import resource
import socket
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.parameters.market_regime.state_v1_0_0 import STATE_PARAMETER_FINGERPRINT
from tip_api.parameters.market_regime.v1_0_0 import PARAMETER_SET_FINGERPRINT
from tip_api.services.etf_relationship_audit import (
    read_etf_relationship_audit,
    validate_tmp_output_dir,
    write_etf_relationship_audit,
)
from tip_api.services.etf_relationship_oracle import compare_with_independent_relationship_oracle
from tip_api.services.etf_relationships import (
    append_etf_relationship_history,
    build_relationship_explanations,
    calculate_etf_relationship_history,
    compare_relationships_with_regime,
    current_relationship_records,
)
from tip_api.services.market_regime_audit import read_market_regime_audit
from tip_api.services.market_regime_sources import load_formal_market_regime_panel
from tip_api.services.market_regime_state_audit import read_market_regime_state_audit


FROZEN_PHASE1A_AUDIT_FINGERPRINT = "d915e86efc14f9bebadfdc4c029afc3d6f0885adaa757f8e9330357d15b22dbf"
FROZEN_PHASE1B_AUDIT_FINGERPRINT = "0f59c9a914e544d7ac5d892ab89fa501d9836a2cd0bce4f675bdeeaac08fa4e8"
PUBLIC_UNIVERSES = (
    "provider_classified_common_shares_v1",
    "provider_classified_common_shares_plus_adrs_v1",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calculate the preregistered Phase 2 ETF Relationship Map offline into a canonical /tmp audit."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true")
    args = parser.parse_args(argv)
    for name in ("data_root", "phase1a_audit", "phase1b_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_','-')} must be absolute")
    if args.verify_output:
        manifest = read_etf_relationship_audit(args.output_dir)
        print(json.dumps(_summary(manifest,args.output_dir),sort_keys=True,separators=(",",":")))
        return 0
    validate_tmp_output_dir(args.output_dir)
    total_started=time.monotonic(); timings={}
    with _offline_socket_guard():
        load_started=time.monotonic()
        phase1a=read_market_regime_audit(args.phase1a_audit)
        phase1b=read_market_regime_state_audit(args.phase1b_audit)
        _validate_phase_audits(phase1a,phase1b,args.as_of_session)
        regime_summaries=_read_regime_summaries(args.phase1b_audit)
        panel=load_formal_market_regime_panel(data_root=args.data_root,as_of_session=args.as_of_session)
        timings["panel_load_seconds"]=_seconds(time.monotonic()-load_started)
        calculation_started=time.monotonic()
        history=calculate_etf_relationship_history(panel=panel)
        current=current_relationship_records(history,as_of_session=args.as_of_session)
        explanations=build_relationship_explanations(current)
        comparisons=compare_relationships_with_regime(records=current,regime_summaries=regime_summaries)
        timings["relationship_calculation_seconds"]=_seconds(time.monotonic()-calculation_started)
        equivalence_started=time.monotonic()
        flags=_equivalence_checks(panel,history)
        if not all(flags.values()):
            raise RuntimeError(f"relationship replay equivalence gate failed: {flags}")
        timings["equivalence_checks_seconds"]=_seconds(time.monotonic()-equivalence_started)
        oracle_started=time.monotonic()
        oracle=compare_with_independent_relationship_oracle(
            panel=panel,records=history,
            append_full_replay_match=flags["append_full_replay_match"],
            input_permutation_match=flags["input_permutation_match"],
            future_prefix_stable=flags["future_prefix_stable"],
        )
        timings["oracle_seconds"]=_seconds(time.monotonic()-oracle_started)
        timings["total_before_artifact_write_seconds"]=_seconds(time.monotonic()-total_started)
        manifest=write_etf_relationship_audit(
            output_dir=args.output_dir,panel=panel,phase1a_manifest=phase1a,phase1b_manifest=phase1b,
            history=history,current=current,explanations=explanations,regime_comparisons=comparisons,
            oracle_report=oracle,first_available_sessions=_first_available_sessions(history),
            generated_at=datetime.now(UTC),timings=timings,
            peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
    print(json.dumps(_summary(manifest,args.output_dir),sort_keys=True,separators=(",",":")))
    return 1 if manifest["oracle_mismatch_count"] or not all(flags.values()) else 0


def _validate_phase_audits(phase1a,phase1b,session):
    if phase1a.get("parameter_set_fingerprint")!=PARAMETER_SET_FINGERPRINT:
        raise RuntimeError("Phase 1a parameter fingerprint mismatch")
    if phase1b.get("state_parameter_fingerprint")!=STATE_PARAMETER_FINGERPRINT:
        raise RuntimeError("Phase 1b parameter fingerprint mismatch")
    if phase1a.get("as_of_session")!=session.isoformat() or phase1b.get("as_of_session")!=session.isoformat():
        raise RuntimeError("Phase 1 audit session mismatch")
    if tuple(phase1a.get("universe_ids",()))!=PUBLIC_UNIVERSES or tuple(phase1b.get("universe_ids",()))!=PUBLIC_UNIVERSES:
        raise RuntimeError("Phase 1 audit Universe catalog mismatch")
    if session==date(2026,8,21):
        if phase1a.get("logical_content_fingerprint")!=FROZEN_PHASE1A_AUDIT_FINGERPRINT:
            raise RuntimeError("frozen Phase 1a audit fingerprint mismatch")
        if phase1b.get("logical_content_fingerprint")!=FROZEN_PHASE1B_AUDIT_FINGERPRINT:
            raise RuntimeError("frozen Phase 1b audit fingerprint mismatch")


def _read_regime_summaries(path):
    payload=json.loads((path/"current-state-summary.json").read_text(encoding="utf-8"))
    records=tuple(payload["records"])
    if tuple(item["universe_id"] for item in records)!=PUBLIC_UNIVERSES:
        raise RuntimeError("Phase 1b current state summary order mismatch")
    return records


def _equivalence_checks(panel,history):
    history_keys=tuple((item.as_of_session,item.pair_id,item.logical_fingerprint) for item in history)
    split_sessions=panel.sessions[5:len(panel.sessions)//2]
    existing=tuple(item for item in history if item.as_of_session in set(split_sessions))
    append_sessions=panel.sessions[len(panel.sessions)//2:]
    suffix=append_etf_relationship_history(panel=panel,existing_history=existing,append_sessions=append_sessions)
    combined=(*existing,*suffix)
    expected=tuple(item for item in history if item.as_of_session in set((*split_sessions,*append_sessions)))
    append_match=tuple(item.logical_fingerprint for item in combined)==tuple(item.logical_fingerprint for item in expected)
    permuted=calculate_etf_relationship_history(panel=replace(panel,bars=tuple(reversed(panel.bars))))
    permutation_match=history_keys==tuple((item.as_of_session,item.pair_id,item.logical_fingerprint) for item in permuted)
    truncated_sessions=panel.sessions[:-1]
    truncated=replace(panel,as_of_session=truncated_sessions[-1],sessions=truncated_sessions,source_sessions=panel.source_sessions[:-1])
    prefix=calculate_etf_relationship_history(panel=truncated)
    expected_prefix=tuple(item for item in history if item.as_of_session<panel.as_of_session)
    future_stable=tuple(item.logical_fingerprint for item in prefix)==tuple(item.logical_fingerprint for item in expected_prefix)
    return {"append_full_replay_match":append_match,"input_permutation_match":permutation_match,"future_prefix_stable":future_stable}


def _first_available_sessions(history):
    output={}
    for window in (5,10,20):
        sessions=[record.as_of_session for record in history for item in record.windows if item.window_sessions==window and item.availability.value=="available"]
        output[f"window_{window}"]=min(sessions).isoformat() if sessions else None
    return output


def _summary(manifest,output_dir):
    return {"status":"completed" if manifest.get("oracle_mismatch_count")==0 else "oracle_mismatch",
            "as_of_session":manifest.get("as_of_session"),"output_dir":str(output_dir),
            "logical_content_fingerprint":manifest.get("logical_content_fingerprint"),
            "history_logical_fingerprint":manifest.get("history_logical_fingerprint"),
            "oracle_mismatch_count":manifest.get("oracle_mismatch_count"),
            "append_full_replay_match":manifest.get("append_full_replay_match"),
            "input_permutation_match":manifest.get("input_permutation_match"),
            "future_prefix_stable":manifest.get("future_prefix_stable"),
            "external_request_count":0,"production_write_count":0}


def _seconds(value): return format(value,".6f")


@contextmanager
def _offline_socket_guard():
    original_socket=socket.socket; original_create=socket.create_connection; original_getaddr=socket.getaddrinfo
    class GuardedSocket(original_socket):
        def connect(self,*args,**kwargs): raise RuntimeError("network prohibited during offline ETF relationship calculation")
        def connect_ex(self,*args,**kwargs): raise RuntimeError("network prohibited during offline ETF relationship calculation")
    def rejected(*args,**kwargs): raise RuntimeError("network prohibited during offline ETF relationship calculation")
    socket.socket=GuardedSocket; socket.create_connection=rejected; socket.getaddrinfo=rejected
    try: yield
    finally: socket.socket=original_socket; socket.create_connection=original_create; socket.getaddrinfo=original_getaddr


if __name__=="__main__":
    raise SystemExit(main())
