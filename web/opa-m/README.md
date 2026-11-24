# OPA-M Site integration

This patch adds the OPA-M research track to the existing Ecosystem tab and hardware roadmap and links the three relevant interactive chips. It targets Sites source revision `1a4fb3f4c7dcc4213249837ff38ebbef0583dd76`.

Apply from this directory to a clean Sites checkout:

```sh
patch="$PWD/site-integration.patch"
git -C /path/to/sites-checkout apply --check "$patch"
git -C /path/to/sites-checkout apply "$patch"
```

Check `/#opa-ecosystem`, `/opa-roadmap.html#opa-m` and the links for Chips 10–12 in the hosted preview. The canonical [research plan](../../research/OPA-M-ROADMAP.md) and [modeling evidence](../../research/OPA-M-001.md) live in the research repository.
