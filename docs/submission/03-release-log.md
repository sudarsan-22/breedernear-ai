# Release log

Every deploy made with `scripts/release.sh`: lint and unit tests, deploy to Cloud Run, live smoke test, then the demo accounts and sample data are reset. The last row before the deadline is the submitted build; to roll back, route traffic to an earlier revision:

```bash
gcloud run services update-traffic breedernear --region asia-south1 --to-revisions <REVISION>=100
```

**Freeze plan:** on 17 Oct, run `MIN_INSTANCES=1 scripts/release.sh`, then make no more changes to `main` (fixes only for a broken live demo, each through this script). On 18 Oct, 9–10 AM, run `scripts/smoke_test.py` on the live URL again before submitting.

| Date | Commit | Cloud Run revision | Min instances | Smoke test |
|---|---|---|---|---|
