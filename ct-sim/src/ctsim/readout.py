"""Rule-based readout: a two-minute summary of a scenario with NO language model and NO API key.

Same shape as the Claude analyst's answer (bottom line, what was run, why, caveats, next step) so the UI can show either.
Every number comes from the scenario result; fact ids point at data/analyst/facts.md. The thresholds below are rules of thumb of this
tool (not clinical or health-economic standards) and are named in the text so a reader can disagree with them.
"""
from __future__ import annotations

from . import scenario

# rules of thumb used for the bottom line; change here, they are also printed in the answer
IDLE_BELOW = 0.60       # share of working days used below which one unit is considered under-used
EXPENSIVE_ABOVE = 1000  # EUR per extra participant above which cost is flagged
TARGETING_ABOVE = 40    # percent of scans that are 'extra' above which targeting is called strong (model-dependent)


def _fmt(x: float) -> str:
    return f"{x:,.0f}"


def describe(scn: dict) -> str:
    reg = scn.get("region")
    area = f"{reg['base']} {reg['radius_km']:.0f} km" if reg else "whole country"
    goal = "reach most people" if scn.get("objective") == "scans" else "reach people hospital CTs miss"
    sites = {"confirmed+likely": "researched CT list (confirmed + likely)", "confirmed": "researched CT list (confirmed only)"}.get(scn.get("ct_sites"), "placeholder CT list")
    if scn.get("fixed_sites") and scn.get("ct_sites") in ("confirmed", "confirmed+likely"):
        sites += " with what-if edits"
    return f"{area}; goal: {goal}; {sites}"


def readout(res: dict, other: dict | None = None) -> str:
    scn = res["scenario"]
    o, c, r = res["outcomes"], res["cost"], res["route"]
    budget = (scn.get("routing") or {}).get("work_days", 200)
    used = r["working_days"] / budget
    share = 100 * o["additional"] / max(o["scans"], 1)
    per_extra = c["per_additional_eur"]

    if used < IDLE_BELOW:
        bottom = (f"One unit would be under-used here: {r['working_days']:.0f} of {budget:.0f} working days, about {_fmt(o['scans'])} scans a year. "
                  f"A single unit is better shared with a neighbouring area than dedicated to this one.")
    elif per_extra > EXPENSIVE_ABOVE:
        bottom = (f"Costly per extra participant (about €{_fmt(per_extra)}). Compare with cheaper ways to raise uptake in this area (invitations, "
                  f"interpreters, evening hours at a hospital CT) before committing to a truck.")
    elif share >= TARGETING_ABOVE:
        bottom = (f"A unit would be well used and well targeted under these assumptions: about {_fmt(o['additional'])} extra participants a year "
                  f"({share:.0f}% of scans). That targeting depends on the assumed uptake curves and the assumed free CT capacity, so test it in a pilot before relying on it.")
    else:
        bottom = (f"A unit would be fully used, but only about {share:.0f}% of its scans reach people a hospital CT would miss "
                  f"(about {_fmt(o['additional'])} extra participants a year). Most scans would replace what a hospital CT could do.")

    lines = ["**Bottom line** " + bottom, "", f"**What I ran** {describe(scn)}."]
    if other:
        lines[-1] += f" Compared with: {describe(other['scenario'])}."
    lines += ["", "**Why**",
              f"- One unit does about {_fmt(o['scans'])} scans a year over {len(r['stops'])} stops, {_fmt(r['km_per_year'])} km of driving and {r['working_days']:.0f} of {budget:.0f} working days (scenario run) [F21].",
              f"- About {_fmt(o['additional'])} of those are extra participants, people the model says a hospital CT would not reach ({share:.0f}%); "
              f"{_fmt(o['additional_in_places_over_60km_from_ct'])} live more than 60 km from a CT (scenario run, assumed CT list) [F20].",
              f"- Cost: about €{_fmt(c['per_scan_eur'])} per scan and €{_fmt(per_extra)} per extra participant, against about €340 for a hospital CT scan with spare capacity (assumptions) [F21]."]
    if other:
        oo, oc, orr = other["outcomes"], other["cost"], other["route"]
        diff = o["additional"] - oo["additional"]
        lines.append(f"- Against the alternative goal: {diff:+,.0f} extra participants a year ({_fmt(o['additional'])} vs {_fmt(oo['additional'])}), "
                     f"{r['km_per_year'] - orr['km_per_year']:+,.0f} km, €{_fmt(per_extra)} vs €{_fmt(oc['per_additional_eur'])} per extra participant.")
    if res.get("reach"):
        rc, cp = res["reach"], res["campaign"]
        lines.append(f"- High-risk group (age 50-74, at least 20 pack-years, current or recent smokers): about {_fmt(rc['eligible_persons'])} people (estimate). Covering them takes about {_fmt(rc['annual_scans_needed'])} scans a year; "
                     f"existing hospital CTs would give {rc['coverage_fixed_only']:.0%} under the assumed spare capacity, and {rc['coverage_with_truck']:.0%} with this plan [F23, F25].")
        if cp["intensity"] > 0:
            lines.append(f"- Campaign (intensity {cp['intensity']:g}): eligible people want {_fmt(cp['demand_eligible'])} scans and ineligible people {_fmt(cp['demand_ineligible'])} after "
                         f"{cp['triage']:.0%} filtering, against {_fmt(cp['free_capacity'])} of assumed free capacity. Longest added wait {cp['longest_extra_wait']['weeks']:g} weeks ({cp['longest_extra_wait']['county']}); "
                         f"{'eligible people are booked first' if cp['priority_eligible'] else 'everyone shares the shortfall'}; the gap equals about {cp['truck_equivalents_of_shortfall']:g} truck-years of scanning [F26].")
    top = sorted(r["stops"], key=lambda s: -s["additional"])[:3]
    if top:
        lines.append("- Biggest contributors: " + "; ".join(f"{s['name']} ({_fmt(s['additional'])} extra, {s['days']:.1f} days)" for s in top) + ".")

    lines += ["", "**Caveats**",
              f"- {res['warnings'][0]}; scanner presence says nothing about capacity or waiting times [F19].",
              "- 'Extra participants' come from assumed uptake curves, an assumed 7% eligible share and assumed costs; they are not lives saved or evidence of benefit [F20].",
              "- Eligible share, CT capacity by county and real uptake in Finland are unknown [known unknowns]; waiting times are modelled, not observed (no county CT wait data was found) [F24].",
              f"- Bottom-line rules of thumb used here: under-used below {IDLE_BELOW:.0%} of working days; costly above €{EXPENSIVE_ABOVE} per extra participant; "
              f"well targeted at {TARGETING_ABOVE}% or more extra scans. These are this tool's rules, not standards.",
              "", "**To reduce uncertainty** Ask the county for CT capacity and waiting times, get Finnish pack-year data for the eligible share, "
              "and run a pilot that randomises invitations to measure how many scans are truly additional."]
    return "\n".join(lines)


def run(scn: dict, compare: bool = True) -> dict:
    """Run the scenario (and, for the equity goal, the 'reach most people' alternative) and return an analyst-shaped answer."""
    res = scenario.run(scn)
    other = None
    if compare and scn.get("objective") != "scans":
        alt = dict(scn, objective="scans")
        alt.pop("monte_carlo", None)
        other = scenario.run(alt)
    scenarios = [{"label": describe(scn), "scenario": scn, "summary": {}}]
    if other:
        scenarios.append({"label": describe(other["scenario"]), "scenario": other["scenario"], "summary": {}})
    return {"answer": readout(res, other), "scenarios": scenarios, "tool_calls": [], "usage": {"api_calls": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
            "model": "rule-based readout (no AI)", "stop_reason": "end_turn", "cached": False}
