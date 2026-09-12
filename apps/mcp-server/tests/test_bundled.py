"""The bundled release is verified, loadable and served without arguments."""

import asyncio
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from swisstip.mcp_server.bundled import bundled_releases, read_manifest
from swisstip.mcp_server.server import main
from swisstip.runtime import ReleaseStore


class BundledReleaseTests(unittest.TestCase):
    def test_manifest_hashes_match_and_bundled_releases_validate(self):
        paths, active = bundled_releases()
        self.assertTrue(paths)
        store = ReleaseStore.from_files(paths, active_release_id=active)
        self.assertEqual(store.active_release_id, active)
        bundle = store.get(active)
        self.assertGreater(len(bundle.facts), 0)
        releases_dir, manifest = read_manifest()
        self.assertEqual(releases_dir.name, "releases")
        entry = next(e for e in manifest["releases"] if e["release_id"] == active)
        self.assertEqual(entry["facts"], len(bundle.facts))

    def test_releases_folder_resolution_order(self):
        from swisstip.mcp_server.bundled import ENVIRONMENT_VARIABLE, locate_releases_dir
        located = locate_releases_dir()
        self.assertTrue((located / "MANIFEST.json").is_file())
        with TemporaryDirectory() as empty:
            with self.assertRaises(FileNotFoundError):
                locate_releases_dir(empty)
            with patch.dict(os.environ, {ENVIRONMENT_VARIABLE: empty}):
                # A wrong environment value is skipped with a note, not fatal, because the walk-up still finds the checkout.
                self.assertEqual(locate_releases_dir(), located)
            with patch.dict(os.environ, {ENVIRONMENT_VARIABLE: str(located)}):
                self.assertEqual(locate_releases_dir(), located)

    def test_server_without_arguments_serves_the_bundled_release(self):
        _, active = bundled_releases()

        async def scenario():
            params = StdioServerParameters(command=sys.executable, args=["-m", "swisstip.mcp_server.server"])
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    root = await session.call_tool("get_coverage", {})
                    self.assertFalse(root.isError)
                    self.assertEqual(root.structuredContent["release_id"], active)
                    self.assertTrue(root.structuredContent["entries"])

        asyncio.run(asyncio.wait_for(scenario(), timeout=90))

    def test_explicit_release_still_requires_an_active_release_id(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as raised:
            main(["--release", "unused.json"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
