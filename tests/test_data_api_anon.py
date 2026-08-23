import os
import urllib.error
import urllib.request

import pytest

from src.config import settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_DB") != "1" or not os.environ.get("ANON_KEY"),
    reason="set RUN_LIVE_DB=1 and ANON_KEY to probe the Data API as anon",
)


def test_anon_data_api_cannot_read_organizations() -> None:
    key = os.environ["ANON_KEY"]
    base = settings.SUPABASE_URL
    assert base is not None
    request = urllib.request.Request(
        f"{base}/rest/v1/organizations?select=id",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
    if status == 200:
        assert body.strip() in {b"[]", b""}
    else:
        assert status in {401, 403, 404}
    assert b"00000000-0000-0000-0000-00000000000a" not in body
