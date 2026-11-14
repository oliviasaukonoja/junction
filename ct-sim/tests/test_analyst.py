import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from ctsim import analyst


def text(t):
    return NS(type="text", text=t)


def tool(i, name, inp):
    return NS(type="tool_use", id=i, name=name, input=inp)


def reply(content, stop):
    return NS(content=content, stop_reason=stop, usage=NS(input_tokens=100, output_tokens=20, cache_read_input_tokens=0, cache_creation_input_tokens=0))


class FakeClient:
    """Duck-typed stand-in for anthropic.Anthropic: scripted replies, records every request."""
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        return self.replies.pop(0)


class BuildScenario(unittest.TestCase):
    def test_translates_and_validates(self):
        s = analyst.build_scenario({"region_base": "tampere", "region_radius_km": 100, "equity_weight": 1, "base_uptake": 0.4, "interval_years": 1})
        self.assertEqual(s["region"], {"base": "Tampere", "radius_km": 100.0})
        self.assertEqual(s["routing"], {"lam": 1.0, "u0": 0.4, "interval": 1.0})
        self.assertEqual(s["ct_sites"], "confirmed+likely")

    def test_rejects_bad_input(self):
        for bad in ({"region_base": "Tampre"}, {"region_base": "Tampere"}, {"region_radius_km": 50}, {"work_days": 5000},
                    {"eligible_share": 0.9}, {"nonsense": 1}, {"ct_sites": "all"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                analyst.build_scenario(bad)

    def test_typo_gets_suggestion(self):
        with self.assertRaises(ValueError) as cm:
            analyst.build_scenario({"region_base": "Tampre", "region_radius_km": 50})
        self.assertIn("Tampere", str(cm.exception))

    def test_campaign_arguments(self):
        s = analyst.build_scenario({"campaign_intensity": 2, "triage": 0.8, "priority_eligible": False, "risk_model": "uniform"})
        self.assertEqual(s["routing"], {"campaign_intensity": 2.0, "triage": 0.8, "priority_eligible": False})
        self.assertEqual(s["risk_model"], "uniform")
        for bad in ({"campaign_intensity": 9}, {"triage": 1.0}):
            with self.assertRaises(ValueError):
                analyst.build_scenario(bad)

    def test_new_tools(self):
        import json as j
        st = {"scenarios": []}
        out, err = analyst.execute("size_pilot", {"control_uptake": 0.4, "uplift": 0.15}, st)
        self.assertFalse(err)
        self.assertEqual(j.loads(out)["invitees_per_arm"], 173)
        _, err = analyst.execute("size_pilot", {"control_uptake": 0.4, "uplift": 0.9}, st)
        self.assertTrue(err)
        out, err = analyst.execute("get_county_data", {"match": "lapland"}, st)
        self.assertFalse(err)
        self.assertEqual(j.loads(out)["counties"][0]["county"], "Lapland")
        out, err = analyst.execute("get_data_status", {}, st)
        self.assertIn("gap", out)
        out, err = analyst.execute("run_scenario", {"region_base": "Tampere", "region_radius_km": 60, "campaign_intensity": 2}, st)
        self.assertFalse(err)
        d = j.loads(out)
        self.assertIn("high_risk_reach", d)
        self.assertIn("MODELLED", d["note"])

    def test_ct_what_if_edits(self):
        s = analyst.build_scenario({"ct_towns_add": ["Kemijärvi"], "ct_towns_remove": ["Kajaani"]})
        self.assertIn("Kemijärvi", s["fixed_sites"])
        self.assertNotIn("Kajaani", s["fixed_sites"])


class Loop(unittest.TestCase):
    def test_tool_loop_end_to_end(self):
        c = FakeClient([
            reply([tool("t1", "run_scenario", {"region_base": "Tampere", "region_radius_km": 80}),
                   tool("t2", "run_scenario", {"region_base": "Tampere", "region_radius_km": 80, "objective": "population"})], "tool_use"),
            reply([text("**Bottom line** test answer")], "end_turn"),
        ])
        r = analyst.ask("Compare plans around Tampere", client=c)
        self.assertEqual(r["answer"], "**Bottom line** test answer")
        self.assertEqual(len(r["scenarios"]), 2)
        self.assertEqual(r["usage"]["api_calls"], 2)
        # request shape: facts in system, tools present, fallbacks opted in, no forced tool_choice, no sampling params
        first = c.requests[0]
        self.assertIn("Facts card", first["system"][0]["text"])
        self.assertEqual({t["name"] for t in first["tools"]}, {"run_scenario", "run_robustness", "get_assumptions", "get_ct_sites", "get_county_data", "get_data_status", "size_pilot"})
        self.assertEqual(first["fallbacks"], "default")
        self.assertNotIn("tool_choice", first)
        self.assertNotIn("temperature", first)
        # second request: assistant tool_use turn, then ONE user message holding BOTH tool_results
        msgs = c.requests[1]["messages"]
        self.assertEqual(msgs[-2]["role"], "assistant")
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertEqual([b["type"] for b in msgs[-1]["content"]], ["tool_result", "tool_result"])
        payload = json.loads(msgs[-1]["content"][0]["content"])
        self.assertIn("extra_participants_per_year", payload)

    def test_bad_tool_input_is_returned_to_the_model_not_raised(self):
        c = FakeClient([reply([tool("t1", "run_scenario", {"region_base": "Atlantis", "region_radius_km": 10})], "tool_use"),
                        reply([text("sorry")], "end_turn")])
        r = analyst.ask("x", client=c)
        res = c.requests[1]["messages"][-1]["content"][0]
        self.assertTrue(res["is_error"])
        self.assertIn("unknown municipality", res["content"])
        self.assertEqual(r["scenarios"], [])

    def test_step_limit_and_refusal_and_call_cap(self):
        loop = FakeClient([reply([tool(f"t{i}", "get_assumptions", {"names": ["u0"]})], "tool_use") for i in range(3)])
        self.assertIn("step limit", analyst.ask("x", client=loop, max_steps=3)["answer"])
        self.assertIn("declined", analyst.ask("y", client=FakeClient([reply([], "refusal")]))["answer"])
        old = analyst._calls
        analyst._calls = analyst.MAX_API_CALLS
        try:
            with self.assertRaises(analyst.AnalystUnavailable):
                analyst.ask("z", client=FakeClient([reply([text("a")], "end_turn")]))
        finally:
            analyst._calls = old

    def test_tools_return_grounding_data(self):
        st = {"scenarios": []}
        a, err = analyst.execute("get_assumptions", {"names": ["eligible_share"]}, st)
        self.assertFalse(err)
        self.assertEqual(json.loads(a)["assumptions"]["eligible_share"]["tag"], "ASSUME")
        s, err = analyst.execute("get_ct_sites", {"match": "kajaani"}, st)
        self.assertFalse(err)
        self.assertGreaterEqual(json.loads(s)["count"], 1)
        _, err = analyst.execute("rm_rf", {}, st)
        self.assertTrue(err)

    def test_record_and_replay_cache(self):
        tmp = Path(tempfile.mkdtemp()) / "cache.json"
        old_cache, old_env = analyst.CACHE, analyst.os.environ.get("CTSIM_ANALYST_RECORD")
        analyst.CACHE = tmp
        analyst.os.environ["CTSIM_ANALYST_RECORD"] = "1"
        try:
            analyst.ask("What is the plan?", client=FakeClient([reply([text("recorded")], "end_turn")]), use_cache=True)
            self.assertTrue(tmp.exists())
            again = analyst.ask("what  is the PLAN?", client=FakeClient([]), use_cache=True)   # empty script: would crash if it called the API
            self.assertTrue(again["cached"])
            self.assertEqual(again["answer"], "recorded")
        finally:
            analyst.CACHE = old_cache
            if old_env is None:
                analyst.os.environ.pop("CTSIM_ANALYST_RECORD", None)
            else:
                analyst.os.environ["CTSIM_ANALYST_RECORD"] = old_env


class NoCredentials(unittest.TestCase):
    def test_missing_key_becomes_friendly_error(self):
        def boom(**kw):
            raise TypeError('"Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set."')
        c = NS(beta=NS(messages=NS(create=boom)))
        with self.assertRaises(analyst.AnalystUnavailable) as cm:
            analyst.ask("anything", client=c)
        self.assertIn("ANTHROPIC_API_KEY", str(cm.exception))


class AskEndpoint(unittest.TestCase):
    def _post(self, base, body):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(base + "/ask", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            return 200, json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_status_codes(self):
        import threading
        from http.server import ThreadingHTTPServer

        from ctsim.server import Handler
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        real = analyst.ask
        try:
            analyst.ask = lambda q, **kw: {"answer": "ok " + q, "scenarios": [], "usage": {}, "model": "m", "cached": False}
            self.assertEqual(self._post(base, {"question": "hi"})[0], 200)
            self.assertEqual(self._post(base, {"question": "hi", "history": [1] * 20})[0], 400)
            def unavailable(q, **kw):
                raise analyst.AnalystUnavailable("no key")
            analyst.ask = unavailable
            code, body = self._post(base, {"question": "hi"})
            self.assertEqual((code, body["error"]), (503, "no key"))
            def explode(q, **kw):
                raise RuntimeError("secret-key-sk-ant-123 leaked?")
            analyst.ask = explode
            code, body = self._post(base, {"question": "hi"})
            self.assertEqual(code, 502)
            self.assertNotIn("secret", body["error"])           # error text must not echo exception details
        finally:
            analyst.ask = real
            srv.shutdown()


class FactsCard(unittest.TestCase):
    def test_card_has_ids_tags_and_unknowns(self):
        t = analyst.FACTS.read_text(encoding="utf-8")
        for fid in ("F1 ", "F9 ", "F14 ", "F20 "):
            self.assertIn(fid, t)
        self.assertIn("Known unknowns", t)
        self.assertGreater(len(t), 3000)


try:
    import anthropic
    import httpx2
except ImportError:
    anthropic = None


@unittest.skipIf(anthropic is None, "anthropic SDK not installed (use .venv)")
class RealSdkWithMockedHttp(unittest.TestCase):
    """The real SDK parses real-shaped JSON; nothing leaves the machine."""
    def test_roundtrip_through_sdk(self):
        seen = []
        script = [
            {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "stop_reason": "tool_use", "stop_sequence": None,
             "content": [{"type": "tool_use", "id": "toolu_1", "name": "run_scenario", "input": {"region_base": "Tampere", "region_radius_km": 60}}],
             "usage": {"input_tokens": 50, "output_tokens": 10}},
            {"id": "msg_2", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "stop_reason": "end_turn", "stop_sequence": None,
             "content": [{"type": "text", "text": "Done."}], "usage": {"input_tokens": 60, "output_tokens": 5}},
        ]

        def handler(request):
            seen.append((request.url.path, request.headers.get("anthropic-beta"), json.loads(request.content)))
            return httpx2.Response(200, json=script.pop(0))

        client = anthropic.Anthropic(api_key="test-key-not-real", http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))
        r = analyst.ask("Plan near Tampere", client=client)
        self.assertEqual(r["answer"], "Done.")
        self.assertEqual(len(r["scenarios"]), 1)
        self.assertEqual(seen[0][0], "/v1/messages")
        self.assertIn("server-side-fallback-2026-07-01", seen[0][1])
        body = seen[0][2]
        self.assertEqual(body["model"], "claude-opus-5-5")
        self.assertEqual(body["fallbacks"], "default")
        self.assertEqual(body["output_config"], {"effort": "medium"})
        second = seen[1][2]["messages"]
        self.assertEqual(second[1]["content"][0]["type"], "tool_use")
        self.assertEqual(second[2]["content"][0]["type"], "tool_result")


if __name__ == "__main__":
    unittest.main()
