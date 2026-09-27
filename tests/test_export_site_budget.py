from scripts import export_site


def item(hash_,size,date,priority=1):
    doc={"versions":[]}
    version={"hash":hash_,"bytes":size}
    return {"hash":hash_,"bytes":size,"date":date,"priority":priority,"doc":doc,"version":version}


def test_publication_selection_reserves_headroom():
    a=item("a",60,"2026-09-27")
    b=item("b",40,"2026-09-26")
    selected,total=export_site.select_publication_candidates([a,b],limit=90)
    assert selected=={"a"}
    assert total==60
    assert a["doc"]["versions"]==[a["version"]]
    assert b["doc"]["versions"]==[]


def test_publication_selection_duplicate_hash_does_not_double_count():
    newest=item("same",60,"2026-09-27")
    older=item("same",60,"2026-09-26")
    selected,total=export_site.select_publication_candidates([older,newest],limit=60)
    assert selected=={"same"}
    assert total==60
    assert newest["doc"]["versions"]==[newest["version"]]
    assert older["doc"]["versions"]==[older["version"]]


def test_default_selection_limit_keeps_five_mib_reserve():
    assert export_site.PUBLIC_PUBLICATION_BUDGET-export_site.PUBLIC_PUBLICATION_SELECTION_LIMIT==5*1024*1024
