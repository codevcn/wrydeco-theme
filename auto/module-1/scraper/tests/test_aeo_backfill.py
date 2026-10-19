import copy
import json
import threading
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from scraper.aeo.backfill import BackfillService, BackfillStore, evidence_digest, product_input, is_duplicate
from scraper.content import content_similarity
from scraper.aeo.backfill_mcp import create_server
from scraper.aeo.shopify_adapter import apply_html
from scraper.errors import ContentValidationError, ShopifyError
from scraper.io_utils import atomic_write_json
from scraper.manifest import parse_manifest_payload
from scraper.server import create_app
from scraper.store import OrchestratorStore, QueueConflict
from scraper.tests.test_aeo import draft


VISUAL = {"design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
          "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"]}


def snapshot(identifier="1", tag="alpha"):
    return {"id": f"gid://shopify/Product/{identifier}", "title": f"{tag} Sculptural Profile Side Table",
            "handle": f"table-{tag}", "createdAt": f"2026-10-{20-int(identifier):02d}T00:00:00Z",
            "descriptionHtml": "<p>A side table with sculptural profile and rounded shelf edges.</p>",
            "productType": "side-table", "variants": {"nodes": [{"selectedOptions": [
                {"name": "Size", "value": '40\'\'Wx 30\'\'H x 16\'\'D'}, {"name": "Finish", "value": "Walnut"}]},
                {"selectedOptions": [{"name": "Size", "value": '47\'\'Wx 32\'\'H x 20\'\'D'}]}]},
            "media": {"nodes": [{"mediaContentType": "IMAGE", "image": {"url": "https://example.test/gallery.jpg"}}]}}


class FakeClient:
    def __init__(self, products, existing=None):
        self.products = products
        self.values = dict(existing or {})
        self.writes = []
        self.pages = []
        self.race = False
        self.fail_readback = False
        self.change_source = False
        self.reads = {}

    def aeo_catalog_page(self, *, after, cutoff):
        self.pages.append((after, cutoff))
        start = int(after or 0)
        end = min(start+2,len(self.products))
        return {"nodes": self.products[start:end], "pageInfo": {"hasNextPage": end<len(self.products), "endCursor": str(end)}}

    def snapshot_product(self, identifier):
        value = copy.deepcopy(next(p for p in self.products if p["id"] == identifier))
        self.reads[identifier] = self.reads.get(identifier,0)+1
        if self.change_source and self.reads[identifier]>1:
            value["title"] += " changed"
        return value

    def read_aeo_metafield(self, identifier):
        return self.values.get(identifier)

    def ensure_aeo_definition(self):
        pass

    def write_aeo_metafield(self, identifier, value, digest):
        if self.race:
            self.values[identifier] = {"type": "multi_line_text_field", "value": "Human edit"}
            raise ShopifyError("Concurrent edit")
        self.writes.append((identifier,value,digest))
        if not self.fail_readback:
            self.values[identifier] = {"type": "multi_line_text_field", "value": value, "compareDigest": "saved"}


class FakeAuthor:
    def __init__(self, fail=()):
        self.fail = fail
        self._shutdown = threading.Event()
        self.calls = []

    def generate(self, db, task):
        self.calls.append(task["product_id"])
        if task["product_id"] in self.fail:
            raise ContentValidationError("Insufficient supported evidence")
        value = draft()
        tag = " ".join(task["handle"].removeprefix("table-") * n for n in (2,3,4,5))
        # Make product-specific fixtures distinguishable for persistent uniqueness checks.
        for entry in [value["overview"], *value["faq"]]:
            key = "text" if "text" in entry else "answer"
            entry[key] = entry[key].replace(" the ", f" the {tag} ").replace(" this ", f" this {tag} ")
        atomic_write_json(db.workspace(task["id"])/"visual_analysis.json", VISUAL)
        db.update_task(task["id"], draft={"aeo":value}, status="ready", reviewed=True)
        return db.validate(task["id"])


@pytest.fixture
def setup(tmp_path,monkeypatch):
    root=tmp_path/"scraper";root.mkdir()
    for name in ["AGENT_BOOTSTRAP_PROMPT.md","CONTENT_TASK_PROMPT.md","AGENT_PROMPT.md"]:
        (root/name).write_text("Use evidence only.")
    (root/"product_types.json").write_text('{"product_types": ["side-table"]}')
    store=OrchestratorStore(root)
    def gallery(urls, directory):
        path=directory/"gallery";path.mkdir(parents=True,exist_ok=True)
        for name in ["001.jpg","002.jpg","contact-sheet.jpg"]:(path/name).write_bytes(b"pixels")
    monkeypatch.setattr("scraper.aeo.backfill.prepare_gallery_evidence",gallery)
    return root,store


def service_for(setup, count=5, existing=None, author=None):
    root,store=setup
    products=[snapshot(str(i),tag) for i,tag in enumerate(["alpha","beta","gamma","delta","epsilon","zeta","eta"],1)][:count]
    client=FakeClient(products,existing)
    service=BackfillService(store,lambda:client,author or FakeAuthor())
    return service,client


def test_exact_success_target_newest_order_pagination_and_batch_isolation(setup):
    service,client=service_for(setup)
    run=service.db.create(3)
    service.process(run["id"])
    result=service.db.run(run["id"])
    assert result["status"]=="completed",result
    assert result["success"]==3
    assert [p[0] for p in client.writes]==[f"gid://shopify/Product/{i}" for i in [1,2,3]]
    assert [p[0] for p in client.pages]==[None,"2"]
    assert len({p[1] for p in client.pages})==1
    with service.store.transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM products").fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM apply_tasks").fetchone()[0]==0


def test_target_completion_releases_unused_draft_without_an_extra_write(setup):
    service,client=service_for(setup,2)
    run=service.db.create(1)
    unused=service.db.add_task(run['id'],client.products[1])
    service.db.update_task(unused['id'],status='ready',reviewed=True)
    service.process(run['id'])
    assert len(client.writes)==1
    assert service.db.task(unused['id'])['status']=='not_needed'
    assert service.db.run(run['id'])['status']=='completed'


def test_existing_and_failed_products_do_not_count_and_exhaustion_is_explicit(setup):
    service,client=service_for(setup,3,{"gid://shopify/Product/1":{"type":"multi_line_text_field","value":"existing"}},
                               FakeAuthor(["gid://shopify/Product/2"]))
    run=service.db.create(3);service.process(run["id"]);result=service.db.run(run["id"])
    assert result["status"]=="exhausted"
    assert result["success"]==1 and result["skipped"]==1 and result["errors"]==1
    assert client.values["gid://shopify/Product/1"]["value"]=="existing"


@pytest.mark.parametrize("quantity",[0,-1,1001,True,1.5,"5",None])
def test_quantity_validation(setup,quantity):
    with pytest.raises(ValueError):BackfillStore(setup[1]).create(quantity)


def test_single_open_job_pause_resume_and_recovery(setup):
    service,client=service_for(setup)
    run=service.db.create(2)
    with pytest.raises(QueueConflict):service.db.create(1)
    service.db.update_run(run["id"],status="paused")
    service.process(run["id"]);assert not client.writes
    service.resume(run["id"]);service.process(run["id"])
    assert service.db.run(run["id"])["success"]==2
    run=service.db.create(1);service.recover()
    assert service.db.run(run["id"])["status"]=="interrupted"


def test_resume_cannot_open_two_jobs_after_a_failed_job(setup):
    service,client=service_for(setup)
    first=service.db.create(1)
    service.db.update_run(first['id'],status='failed')
    second=service.db.create(1)
    with pytest.raises(QueueConflict,match='job AEO khác'):
        service.resume(first['id'])
    assert service.db.run(first['id'])['status']=='failed'
    assert service.db.run(second['id'])['status']=='queued'


def test_retry_failed_product_after_catalog_exhaustion_respects_target(setup):
    author=FakeAuthor(['gid://shopify/Product/1'])
    service,client=service_for(setup,2,author=author)
    run=service.db.create(2);service.process(run['id'])
    result=service.db.run(run['id']);assert result['status']=='exhausted' and result['success']==1
    failed=next(t for t in result['tasks'] if t['status']=='error')
    author.fail=()
    service.retry_task(failed['id']);service.process(run['id'])
    result=service.db.run(run['id'])
    assert result['status']=='completed' and result['success']==2 and result['errors']==0
    assert len(client.writes)==2


def test_read_connection_failure_stops_without_advancing_cursor(setup):
    import requests
    service,client=service_for(setup,2)
    original=client.read_aeo_metafield
    def disconnected(*args):raise requests.ConnectionError('Connection closed')
    client.read_aeo_metafield=disconnected
    run=service.db.create(1)
    with pytest.raises(ShopifyError,match='Connection closed'):service.process(run['id'])
    result=service.db.run(run['id']);assert result['page_index']==0
    assert not client.writes
    service.db.update_run(run['id'],status='failed')
    client.read_aeo_metafield=original
    service.resume(run['id']);service.process(run['id'])
    assert service.db.run(run['id'])['success']==1 and len(client.writes)==1


def test_resume_after_unknown_write_does_not_double_count_or_overwrite(setup):
    service,client=service_for(setup,1)
    run=service.db.create(1);task=service.db.add_task(run["id"],client.products[0])
    service.process_product(client,task)
    service.db.update_task(task["id"],status="ready") # Simulate crash after mutation before persisted completion.
    service.process(run["id"])
    result=service.db.run(run["id"])
    assert result["status"]=="completed" and result["success"]==1
    assert len(client.writes)==1


def test_concurrent_edit_preserved_and_not_counted(setup):
    service,client=service_for(setup,1);client.race=True
    run=service.db.create(1);service.process(run["id"])
    assert service.db.run(run["id"])["success"]==0
    assert client.values[client.products[0]["id"]]["value"]=="Human edit"


def test_changed_source_blocks_write(setup):
    service,client=service_for(setup,1);client.change_source=True
    run=service.db.create(1);service.process(run["id"])
    assert not client.writes
    assert "evidence changed" in service.db.run(run["id"])["tasks"][0]["error"]


def test_no_unreviewed_draft_can_be_written(setup):
    class Unreviewed(FakeAuthor):
        def generate(self,db,task):
            super().generate(db,task);db.update_task(task["id"],reviewed=False)
    service,client=service_for(setup,1,author=Unreviewed())
    run=service.db.create(1);service.process(run["id"])
    assert not client.writes
    assert "review" in service.db.run(run["id"])["tasks"][0]["error"]


def test_shopify_failure_stops_without_automatic_retry(setup):
    service,client=service_for(setup,2);client.fail_readback=True
    run=service.db.create(1)
    with pytest.raises(ShopifyError):service.process(run["id"])
    assert len(client.writes)==2 # Existing adapter's bounded independent verification.
    assert len(service.author.calls)==1


def test_unknown_network_outcome_stops_then_reconciles_without_overcount(setup):
    service,client=service_for(setup,2)
    original=client.write_aeo_metafield
    def timeout_after_write(*args):
        original(*args)
        raise TimeoutError("Response lost after Shopify accepted the write")
    client.write_aeo_metafield=timeout_after_write
    run=service.db.create(1)
    with pytest.raises(ShopifyError,match="reconciliation"):
        service.process(run["id"])
    assert len(client.writes)==1
    service.db.update_run(run["id"],status="failed")
    service.resume(run["id"]);service.process(run["id"])
    assert service.db.run(run["id"])["success"]==1
    assert len(client.writes)==1


def test_catalog_nonempty_aeo_is_skipped_without_extra_reads(setup):
    service,client=service_for(setup,1)
    client.products[0]["aeo"]={"type":"multi_line_text_field","value":"Existing HTML"}
    def forbidden(*args):raise AssertionError("Existing catalog AEO should not need another request")
    client.read_aeo_metafield=forbidden
    run=service.db.create(1);service.process(run["id"])
    assert service.db.run(run["id"])["status"]=="exhausted"
    assert service.db.run(run["id"])["skipped"]==1
    assert not client.writes


def test_cross_product_exact_duplicate_is_blocked(setup):
    service,client=service_for(setup,2)
    run=service.db.create(2)
    first=service.db.add_task(run["id"],client.products[0]);service.process_product(client,first)
    second=service.db.add_task(run["id"],client.products[1]);workspace=service.db.workspace(second["id"])
    workspace.mkdir(parents=True)
    atomic_write_json(workspace/'shopify_before.json',client.products[1])
    atomic_write_json(workspace/'visual_analysis.json',VISUAL)
    service.db.update_task(second["id"],draft=service.db.task(first["id"])["draft"])
    with pytest.raises(ContentValidationError,match="duplicates"):
        service.db.validate(second["id"])


@pytest.mark.parametrize('left,right',[
    ('',''),('alpha beta gamma','alpha beta gamma'),
    ('alpha beta gamma delta','unrelated words describe another product'),
    ('<p>sculptural console table with curved base</p>','sculptural console table with curved base'),
    ('The table has a curved sculptural outline. '*20,'The table has a curved sculptural profile. '*20),
    ('alpha beta gamma delta epsilon '*20,'epsilon delta gamma beta alpha '*20),
])
def test_duplicate_prefilter_preserves_shared_scorer_decision(left,right):
    assert is_duplicate(left,right)==(content_similarity('aeo_html',left,right)>=.97)


def test_duplicate_prefilter_never_discards_character_near_matches():
    import random
    randomizer=random.Random(42)
    base='The sculptural console features a flowing profile and an elongated tabletop. '*8
    for edits in [1,3,10,20,60]:
        for _ in range(4):
            chars=list(base)
            for _ in range(edits):
                index=randomizer.randrange(len(chars))
                if randomizer.choice([True,False]):chars.insert(index,randomizer.choice(' abcdef'))
                else:chars.pop(index)
            other=''.join(chars)
            assert is_duplicate(base,other)==(content_similarity('aeo_html',base,other)>=.97)


def test_input_is_product_only_and_preserves_axis_units(setup):
    value=snapshot();value["descriptionHtml"]='<script>Secret</script><p>Actual product facts</p>'
    context=product_input(value)
    assert "Secret" not in json.dumps(context)
    assert "Actual product facts" in json.dumps(context)
    assert context["identity"]["asin"]==value["id"]
    assert "40" in context["facts"][3]["text"]
    changed=copy.deepcopy(value);changed["seo"]={"title":"unrelated"}
    assert evidence_digest(value)==evidence_digest(changed)


def test_active_backfill_locks_batch_product_and_existing_batch_locks_backfill(setup):
    service,client=service_for(setup,1)
    run=service.db.create(1);task=service.db.add_task(run["id"],client.products[0])
    service.db.update_task(task["id"],status="authoring")
    payload={"products":[{"amazon_url":"https://www.amazon.com/dp/B000000001","shopify_product_id":"1"}]}
    manifest=parse_manifest_payload(payload,setup[0]/"input.json")
    with pytest.raises(QueueConflict,match="store AEO"):setup[1].create_run(manifest,payload,{})
    # A completed job must release an unused ready draft's product reservation.
    service.db.update_run(run["id"],status="completed")
    setup[1].create_run(manifest,payload,{})
    service.db.update_run(run["id"],status="paused")
    service.db.update_task(task["id"],status="pending")
    with pytest.raises(ContentValidationError,match="Amazon batch"):service.process_product(client,task)
    assert not client.writes


def test_api_csrf_validation_and_preview_does_not_mutate_shopify(setup):
    root,store=setup;service,client=service_for(setup,1)
    app=create_app(root,store=store,shopify_client_factory=lambda:client)
    browser=app.test_client();csrf=browser.get('/api/bootstrap').json['csrf_token']
    assert browser.post('/api/aeo-backfill',json={'quantity':1}).status_code==403
    headers={'X-CSRF-Token':csrf,'Origin':'http://localhost'}
    assert browser.post('/api/aeo-backfill',json={'quantity':0},headers=headers).status_code==400
    result=browser.post('/api/aeo-backfill',json={'quantity':1},headers=headers)
    assert result.status_code==201
    assert not client.writes
    assert browser.get('/api/aeo-backfill').json['runs'][0]['target']==1
    assert 'contract' not in browser.get('/api/aeo-backfill').json['runs'][0]


@pytest.mark.asyncio
async def test_mcp_assigned_task_gallery_context_validation_and_review_lock(setup,monkeypatch):
    root,store=setup;service,client=service_for(setup,1)
    run=service.db.create(1);task=service.db.add_task(run['id'],client.products[0]);tid=task['id']
    directory=service.db.workspace(tid);directory.mkdir(parents=True)
    atomic_write_json(directory/'shopify_before.json',client.products[0])
    gallery=directory/'evidence'/'gallery';gallery.mkdir(parents=True)
    for name in ['001.jpg','002.jpg','contact-sheet.jpg']:(gallery/name).write_bytes(b'image')
    service.db.update_task(tid,status='authoring')
    monkeypatch.setenv('WRYDECO_EXPECTED_TASK_ID',tid)
    monkeypatch.setenv('WRYDECO_AGENT_SESSION_ID','test-worker')
    server=create_server(root,store)
    tools={tool.name:tool.fn for tool in server._tool_manager.list_tools()}
    with pytest.raises(ToolError):tools['claim_expected_content_task']('other')
    tools['claim_expected_content_task'](tid)
    with pytest.raises(ToolError):tools['get_content_context']('other')
    with pytest.raises(ToolError):tools['read_evidence']('../.env')
    with pytest.raises(ToolError):tools['write_content_draft']({'aeo':draft()})
    tools['get_content_context']()
    for name in ['001.jpg','002.jpg','contact-sheet.jpg']:tools['read_evidence']('gallery/'+name)
    tools['write_visual_analysis']({'target_identity':'Sculptural Side Table','evidence_ids':['gallery/001.jpg'],**VISUAL})
    with pytest.raises(ToolError):tools['write_content_draft']({'aeo':draft()})
    tools['get_content_context']()
    with pytest.raises(ToolError):tools['write_content_draft']({'title':'SEO','aeo':draft()})
    tools['write_content_draft']({'aeo':draft()})
    assert tools['validate_content_draft']()['valid']
    assert tools['finalize_content']()['state']=='ready_for_review'
    assert not service.db.task(tid)['reviewed']
    service.db.update_task(tid,status='written')
    with pytest.raises(ToolError):tools['write_content_draft']({'aeo':draft()})
