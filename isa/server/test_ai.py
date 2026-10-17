import json
import os
import tempfile
import unittest
from unittest.mock import patch
import ai
import store

META = {"provider":"aws-bedrock","model":"test-only","request_id":"synthetic","usage":{"inputTokens":10,"outputTokens":10}}

class AITest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"ISA_AI_ENABLED":"1","ISA_ENV":"lab","ISA_ERASURE_LEDGER":self.folder.name+"/erasures"})
        self.env.start()
        self.clock = patch.object(store, "today", return_value="2026-10-16")
        self.clock.start()
        self.conn = store.connect(self.folder.name+"/test.sqlite")
        self.owner = store.ensure_identity(self.conn, "synthetic-one")
        self.other = store.ensure_identity(self.conn, "synthetic-two")
    def tearDown(self):
        self.conn.close()
        self.clock.stop()
        self.env.stop()
        self.folder.cleanup()
    def entry(self):
        return store.save_entry(self.conn,self.owner,{"id":"padaria","merchant":"Padaria Exemplo","nature":"consumo","direction":"gasto","amountMinor":2790,"category":"","status":"pago","statusDate":"2026-10-16"})
    def test_category_persisted_no_value_change_and_no_duplicate(self):
        self.entry()
        ai.queue_categories(self.conn,self.owner)
        ai.queue_categories(self.conn,self.owner)
        self.assertEqual(store.one(self.conn,"SELECT COUNT(*) AS n FROM ai_job")["n"],1)
        with patch.object(ai,"invoke",return_value=({"items":[{"id":"padaria","category":"Alimentação","clear":True,"reason":"Compra na padaria."}]},META)):
            ai.work_once(self.conn)
        saved=ai.entries(self.conn,self.owner)[0]
        self.assertEqual((saved["category"],saved["amountMinor"]),("Alimentação",2790))
        self.assertEqual(ai.entries(self.conn,self.other),[])
        self.assertEqual(store.one(self.conn,"SELECT origin FROM suggestion")["origin"],"ia-real")
        self.conn.close()
        self.conn=store.connect(self.folder.name+"/test.sqlite")
        self.assertEqual(ai.entries(self.conn,self.owner)[0]["category"],"Alimentação")
    def test_human_change_wins_late_response(self):
        original=self.entry()
        ai.queue_categories(self.conn,self.owner)
        def respond(*args,**kwargs):
            store.save_entry(self.conn,self.owner,dict(original,category="Compras"))
            return {"items":[{"id":"padaria","category":"Alimentação","clear":True,"reason":"Padaria."}]},META
        with patch.object(ai,"invoke",side_effect=respond):
            ai.work_once(self.conn)
        saved=ai.entries(self.conn,self.owner)[0]
        self.assertEqual(saved["category"],"Compras")
        self.assertTrue(saved["userLocked"])
    def test_invalid_id_fails_without_modifying_entry(self):
        self.entry()
        ai.queue_categories(self.conn,self.owner)
        with patch.object(ai,"invoke",return_value=({"items":[{"id":"another-person","category":"Alimentação","clear":True,"reason":"Não permitido."}]},META)):
            ai.work_once(self.conn)
        self.assertEqual(ai.entries(self.conn,self.owner)[0]["category"],"")
        self.assertEqual(store.one(self.conn,"SELECT status FROM ai_job")["status"],"failed")
    def test_plan_numbers_acceptance_and_stale(self):
        store.load_october(self.conn,self.owner)
        job=ai.queue_plan(self.conn,self.owner,{})
        payload=json.loads(store.one(self.conn,"SELECT payload_json FROM ai_job WHERE id = ?",(job["id"],))["payload_json"])
        option=next(o for o in payload["options"] if o["label"]=="Aluguel")
        output={"summary":"O dinheiro fica curto antes da entrada.","next_step":"Converse sobre a data antes de decidir.","question":"","option_id":option["id"],"source_ids":[]}
        with patch.object(ai,"invoke",return_value=(output,META)):
            ai.work_once(self.conn)
        plan=ai.status(self.conn,self.owner)["plans"][0]["result"]
        self.assertEqual(plan["current"]["minimum"]["cents"],-10000)
        self.assertEqual(plan["option"]["result"]["minimum"]["cents"],40000)
        self.assertIsNone(ai.decision(self.conn,self.other,plan["suggestionId"],{"event":"aceita"}))
        ai.decision(self.conn,self.owner,plan["suggestionId"],{"event":"aceita"})
        ai.decision(self.conn,self.owner,plan["suggestionId"],{"event":"aceita"})
        self.assertEqual(store.one(self.conn,"SELECT COUNT(*) AS n FROM scenario")["n"],1)
        self.assertEqual(store.one(self.conn,"SELECT due_on FROM commitment WHERE label = 'Aluguel'")["due_on"],"2026-10-20")
        store.add_commitment(self.conn,self.owner,{"label":"Nova conta","totalCents":900,"dueOn":"2026-10-18"})
        self.assertTrue(ai.status(self.conn,self.owner)["plans"][0]["result"]["stale"])
    def test_quota_blocks_provider(self):
        self.entry()
        ai.queue_categories(self.conn,self.owner)
        with patch.dict(os.environ,{"ISA_AI_DAILY_USER_CALLS":"0"}),patch.object(ai,"invoke") as model:
            ai.work_once(self.conn)
            model.assert_not_called()
        self.assertEqual(store.one(self.conn,"SELECT error_code FROM ai_job")["error_code"],"daily_limit")
    def test_backup_contains_work_and_suggestions(self):
        self.entry()
        ai.queue_categories(self.conn,self.owner)
        self.assertIn("ai_job",store.SNAPSHOT_TABLES)
        self.assertIn("ai_job",store.OWNER_TABLES)
        store.forget_owner(self.conn,None,self.owner)
        self.assertEqual(store.one(self.conn,"SELECT COUNT(*) AS n FROM ai_job")["n"],0)

if __name__ == "__main__":
    unittest.main()
