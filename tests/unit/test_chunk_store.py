"""
tests/unit/test_chunk_store.py
------------------------------
Unit tests for the CDC dedup chunk store.
No database or filesystem required — uses in-memory stubs.
"""
import hashlib
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from dedup.chunk_store import (
    ChunkStore,
    _chunk_path,
    _rabin_cdc_chunks,
    Chunk,
)


# ── CDC chunker tests ─────────────────────────────────────────────────────────

class TestRabinCDC:
    def test_empty_input_yields_nothing(self):
        chunks = list(_rabin_cdc_chunks(b""))
        assert chunks == []

    def test_small_input_yields_one_chunk(self):
        data = b"hello world"
        chunks = list(_rabin_cdc_chunks(data, min_size=1, target_size=16, max_size=64))
        assert len(chunks) == 1
        assert chunks[0][1] == data

    def test_chunks_cover_all_data(self):
        data = os.urandom(256 * 1024)  # 256 KB of random bytes
        chunks = list(_rabin_cdc_chunks(data, min_size=512, target_size=4096, max_size=16384))
        reconstructed = b"".join(c for _, c in chunks)
        assert reconstructed == data

    def test_offsets_are_contiguous(self):
        data = os.urandom(64 * 1024)
        chunks = list(_rabin_cdc_chunks(data, min_size=512, target_size=4096, max_size=16384))
        expected_offset = 0
        for offset, chunk_bytes in chunks:
            assert offset == expected_offset
            expected_offset += len(chunk_bytes)
        assert expected_offset == len(data)

    def test_chunk_sizes_within_bounds(self):
        data = os.urandom(256 * 1024)
        min_s, max_s = 512, 16384
        chunks = list(_rabin_cdc_chunks(data, min_size=min_s, target_size=4096, max_size=max_s))
        # Last chunk can be smaller than min_size
        for _, c in chunks[:-1]:
            assert min_s <= len(c) <= max_s

    def test_deterministic_same_data_same_boundaries(self):
        data = os.urandom(128 * 1024)
        c1 = [sha for _, c in _rabin_cdc_chunks(data) for sha in [hashlib.sha256(c).hexdigest()]]
        c2 = [sha for _, c in _rabin_cdc_chunks(data) for sha in [hashlib.sha256(c).hexdigest()]]
        assert c1 == c2

    def test_dedup_identical_blocks(self):
        """
        Repeated identical blocks of structured data should produce duplicate
        chunk hashes once CDC finds the recurring boundaries.

        Note: os.urandom produces random bytes with no recurring fingerprint
        patterns, so CDC will find different boundaries each repetition.
        We use structured/patterned data here — the same pattern that would
        appear in real VM disk images (OS files, zero blocks, etc.).
        """
        # Use a deterministic byte pattern (simulates repeated OS file data)
        block = bytes(range(256)) * 32  # 8 KB of 0x00..0xFF repeated
        data = block * 8   # 64 KB of 8 identical structured blocks
        chunks = list(_rabin_cdc_chunks(data, min_size=512, target_size=4096, max_size=16384))
        hashes = [hashlib.sha256(c).hexdigest() for _, c in chunks]
        unique_hashes = set(hashes)
        # Structured repeated data produces recurring fingerprint boundaries →
        # many identical chunks. Unique count << total chunk count.
        assert len(unique_hashes) < len(hashes), (
            f"Expected dedup: {len(hashes)} chunks but all {len(unique_hashes)} unique"
        )

    def test_one_byte_change_minimal_impact(self):
        """
        Changing one byte should only affect the chunks around that byte,
        not all subsequent chunks (content-defined boundaries are stable).
        """
        data = os.urandom(256 * 1024)
        modified = bytearray(data)
        modified[128 * 1024] ^= 0xFF  # Flip a byte in the middle

        original_chunks = {hashlib.sha256(c).hexdigest() for _, c in _rabin_cdc_chunks(data)}
        modified_chunks = {hashlib.sha256(c).hexdigest() for _, c in _rabin_cdc_chunks(bytes(modified))}

        common = original_chunks & modified_chunks
        # CDC boundary stability: chunks far from the changed byte are unaffected.
        # The changed byte and its two neighbouring chunks will differ; the rest
        # should be identical. Require at least 30% overlap (conservative).
        assert len(common) >= len(original_chunks) * 0.3


# ── ChunkStore write / read tests ─────────────────────────────────────────────

@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    return tmp_path / "chunks"


@pytest.fixture
def mock_db():
    """In-memory dict-backed chunk index stub."""
    index: dict[str, dict] = {}

    db = AsyncMock()

    async def execute_stub(query, params=None):
        q = str(query)
        result = MagicMock()

        if "SELECT sha256" in q and params:
            sha = params.get("h", "")
            row = index.get(sha)
            result.mappings.return_value.first.return_value = row
        elif "INSERT INTO chunks" in q and params:
            sha = params["h"]
            if sha not in index:
                index[sha] = {
                    "sha256": sha,
                    "compressed_bytes": params["c"],
                    "ref_count": 1,
                }
            else:
                index[sha]["ref_count"] += 1
        elif "UPDATE chunks SET ref_count = ref_count + 1" in q and params:
            sha = params["h"]
            if sha in index:
                index[sha]["ref_count"] += 1
        elif "UPDATE chunks SET ref_count = GREATEST" in q and params:
            sha = params["h"]
            if sha in index:
                index[sha]["ref_count"] = max(0, index[sha]["ref_count"] - 1)
        elif "DELETE FROM chunks" in q and params:
            sha = params["h"]
            if sha in index and index[sha]["ref_count"] == 0:
                del index[sha]
        elif "ref_count = 0" in q:
            zeros = [{"sha256": k, "store_path": f"/fake/{k}"} for k, v in index.items() if v["ref_count"] == 0]
            result.mappings.return_value.all.return_value = zeros
        return result

    db.execute.side_effect = execute_stub
    db.commit = AsyncMock()
    db._index = index  # Expose for assertions
    return db


class TestChunkStore:
    @pytest.mark.asyncio
    async def test_write_and_read_roundtrip(self, store_root, mock_db):
        store = ChunkStore(store_root, mock_db, min_chunk=16, target_chunk=64, max_chunk=256, compress=False)
        data = os.urandom(1024)

        manifest = await store.write_disk("vm-1", "disk-1", data)
        recovered = await store.read_manifest(manifest)

        assert recovered == data

    @pytest.mark.asyncio
    async def test_dedup_second_write_no_new_files(self, store_root, mock_db):
        store = ChunkStore(store_root, mock_db, min_chunk=16, target_chunk=64, max_chunk=256, compress=False)
        data = os.urandom(512)

        m1 = await store.write_disk("vm-1", "disk-1", data)
        files_after_first = list(store_root.rglob("*"))

        m2 = await store.write_disk("vm-2", "disk-1", data)  # Same data, different VM
        files_after_second = list(store_root.rglob("*"))

        # No new files should have been created
        assert set(f.name for f in files_after_first) == set(f.name for f in files_after_second)
        # But ref counts should be 2 in the index
        for ref in m1.chunk_refs:
            assert mock_db._index[ref["sha256"]]["ref_count"] == 2

    @pytest.mark.asyncio
    async def test_dedup_ratio_repeated_blocks(self, store_root, mock_db):
        store = ChunkStore(store_root, mock_db, min_chunk=64, target_chunk=256, max_chunk=1024, compress=False)
        block = b"A" * 512
        data = block * 16   # 8 KB of identical 512-byte blocks

        manifest = await store.write_disk("vm-1", "disk-1", data)

        # With identical content, dedup ratio should be > 2x
        assert manifest.dedup_ratio > 2.0

    @pytest.mark.asyncio
    async def test_gc_removes_orphan_chunks(self, store_root, mock_db):
        store = ChunkStore(store_root, mock_db, min_chunk=16, target_chunk=64, max_chunk=256, compress=False)
        data = os.urandom(256)

        manifest = await store.write_disk("vm-1", "disk-1", data)

        # Decrement all refs to 0 (simulates manifest deletion)
        await store.decrement_refs(manifest.chunk_refs)

        # All chunks should be at ref_count 0
        for ref in manifest.chunk_refs:
            assert mock_db._index[ref["sha256"]]["ref_count"] == 0

        # GC should delete them
        result = await store.gc()
        assert result["deleted"] > 0

    @pytest.mark.asyncio
    async def test_chunk_files_use_two_level_paths(self, store_root, mock_db):
        store = ChunkStore(store_root, mock_db, min_chunk=16, target_chunk=64, max_chunk=256, compress=False)
        data = os.urandom(128)
        await store.write_disk("vm-1", "disk-1", data)

        chunk_files = list(store_root.rglob("*"))
        chunk_files = [f for f in chunk_files if f.is_file()]
        for f in chunk_files:
            # Path structure: STORE_ROOT / xx / yyyyyy...
            assert len(f.parent.name) == 2, f"Expected 2-char dir, got {f.parent.name!r}"


# ── Storage path helper tests ─────────────────────────────────────────────────

def test_chunk_path_structure():
    root = Path("/store")
    sha = "abcdef1234567890" * 4  # 64 char hex
    path = _chunk_path(root, sha)
    assert path == root / "ab" / ("cdef1234567890" * 4 + "ab"[2:] if False else sha[2:])
    assert path.parts[-2:] == ("ab", sha[2:])
