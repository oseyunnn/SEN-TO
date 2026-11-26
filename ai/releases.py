"""Offline review gates and immutable cloud publication helpers."""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from ai.validator import is_safe_source_url
from ai.vector_store import _prepare_chunks, _metadata_for, VectorStoreError


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def prepare_release(chunks, review, source_root):
    """Approval is a human assertion bound to exact input bytes, never inferred from VERIFIED."""
    require(review.get('release_id') and review.get('collection'), 'Release ID and collection are required.')
    subjects = review.get('subjects', [])
    require(len(subjects) == 2 and len(set(subjects)) == 2, 'The pilot must identify exactly two subjects.')
    require(valid_date(review.get('reviewed_at')), 'A dated review is required.')
    scope = review.get('scope_review', [])
    require(len(scope) == 2 and {s.get('senator_id') for s in scope} == set(subjects)
            and {s.get('bloc') for s in scope} == {'majority', 'minority'},
            'Pilot selection requires reviewed majority/minority scope evidence.')
    for item in scope:
        require(item.get('reviewer') and valid_date(item.get('reviewed_at')) and valid_date(item.get('as_of')),
                'Scope classification requires a reviewer and dated as-of check.')
        source = item.get('source', {})
        require(all(source.get(k) for k in ('title', 'issuing_body', 'source_url', 'retrieved_at', 'relevant_period', 'locator'))
                and is_safe_source_url(source.get('source_url')) and source.get('verification_status') == 'verified',
                'Scope classification requires traceable original-source provenance.')
    decisions = review.get('decisions', [])
    approved = [d for d in decisions if d.get('decision') == 'approved']
    require(approved, 'No human-approved claims are available. Research labels alone cannot be published.')
    by_key = {}
    for decision in approved:
        key = (decision.get('senator_id'), decision.get('claim_id'))
        require(key not in by_key, 'Duplicate approval.')
        require(key[0] in subjects and key[1], 'Approval is outside the pilot scope.')
        require(decision.get('reviewer') and valid_date(decision.get('reviewed_at')), 'Reviewer and review date are required.')
        require(re.fullmatch(r'[0-9a-f]{64}', decision.get('source_sha256', '')), 'Approval must bind the source checksum.')
        require(decision.get('congress_id') in {'19', '20', 'historical'}, 'Review must normalize Congress or label historical evidence.')
        require(decision.get('period_basis'), 'Record the source-supported basis for the normalized period.')
        by_key[key] = decision
    selected, matched = [], set()
    for original in chunks:
        key = (original.get('senator_id'), original.get('claim_id'))
        if key not in by_key:
            continue
        decision = by_key[key]
        require(original.get('source_sha256') == decision['source_sha256'], 'Reviewed claim changed; review again.')
        filename = original.get('source_file', '')
        require(filename and Path(filename).name == filename, 'Invalid source filename.')
        source = Path(source_root) / filename
        require(source.is_file() and checksum(source) == decision['source_sha256'], 'Source file does not match reviewed bytes.')
        require(original.get('verification_status') == 'verified', 'An approved claim lacks complete importer provenance.')
        associations = set(original.get('senator_ids', [])) | {original.get('senator_id')}
        require(associations <= set(subjects), 'A claim has unreviewed subject associations.')
        require(all((subject, original['claim_id']) in by_key for subject in associations), 'Every shared subject association requires approval.')
        sources = original.get('citation_sources', [])
        require(sources, 'Every claim needs citations.')
        checked = decision.get('sources', [])
        for citation in sources:
            require(all(citation.get(k) for k in ('title', 'issuing_body', 'source_url', 'retrieved_at', 'relevant_period', 'locator')), 'Incomplete source provenance.')
            require(citation.get('verification_status') == 'verified' and is_safe_source_url(citation['source_url']), 'Unsafe or unverified source.')
            require(any(s.get('source_url') == citation['source_url'] and s.get('locator') == citation['locator'] for s in checked), 'Human review must cover every original source and exact locator.')
        record = {**original, 'congress_id': decision['congress_id'], 'reviewed_at': decision['reviewed_at'], 'release_id': review['release_id']}
        selected.append(record)
        matched.update((subject, original['claim_id']) for subject in associations)
    require(matched == set(by_key), 'Some approved claims are absent from the supplied chunks.')
    rows = _prepare_chunks(selected)
    counts = dict(Counter(r['senator_id'] for r in rows))
    require(set(counts) == set(subjects), 'Both pilot subjects need reviewed evidence.')
    require(len({c['chunk_id'] for c in selected}) == len(selected), 'Duplicate chunks are not allowed.')
    preflight_rows(rows)
    manifest = {'release_id': review['release_id'], 'collection': review['collection'], 'schema_version': '2',
                'embedding_provider': 'openai', 'embedding_model': 'text-embedding-3-small',
                'embedding_dimensions': 1536, 'distance_metric': 'cosine', 'reviewed_at': review['reviewed_at'],
                'subjects': subjects, 'scope_review': scope, 'expected_counts': counts, 'expected_rows': len(rows),
                'approved_ids': sorted(c['chunk_id'] for c in selected),
                'source_checksums': {c['source_file']: c['source_sha256'] for c in selected},
                'importer_versions': sorted({c['extraction_version'] for c in selected})}
    return selected, manifest


def preflight_rows(rows):
    require(bool(rows), 'A release cannot be empty.')
    for row in rows:
        require(len(row['index_id'].encode('utf-8')) <= 128, 'Cloud ID exceeds 128 bytes.')
        require(len(row['text'].encode('utf-8')) <= 16384, 'Cloud document exceeds 16384 bytes.')
        require(all(len(str(v).encode('utf-8')) <= 8182 for v in _metadata_for(row).values()), 'Cloud metadata exceeds 8182 bytes; do not truncate evidence.')


def validate_package(chunks, manifest, config):
    require(manifest.get('collection') == config.collection and manifest.get('release_id') == config.release, 'Destination differs from the release manifest.')
    for key, value in config.metadata().items():
        require(manifest.get(key) == value, 'Release embedding/schema identity mismatch.')
    require(sorted(c.get('chunk_id', '') for c in chunks) == manifest.get('approved_ids'), 'Release allowlist does not match chunks.')
    require(all(c.get('release_id') == config.release and c.get('congress_id') in {'19', '20', 'historical'} for c in chunks), 'Unreviewed release or period metadata.')
    require(all(c.get('verification_status') == 'verified' and valid_date(c.get('reviewed_at'))
                and c.get('source_sha256') == manifest.get('source_checksums', {}).get(c.get('source_file'))
                for c in chunks), 'Release contains unreviewed or changed source data.')
    for chunk in chunks:
        sources = chunk.get('citation_sources', [])
        require(sources and all(is_safe_source_url(s.get('source_url')) and s.get('verification_status') == 'verified'
                    and all(s.get(k) for k in ('title', 'issuing_body', 'retrieved_at', 'relevant_period', 'locator')) for s in sources),
                'Release source provenance is incomplete.')
    rows = _prepare_chunks(chunks)
    preflight_rows(rows)
    counts = dict(Counter(r['senator_id'] for r in rows))
    require(counts == manifest.get('expected_counts') and len(rows) == manifest.get('expected_rows'), 'Release counts differ from the manifest.')
    require(set(counts) == set(manifest.get('subjects', [])) and len(counts) == 2, 'Invalid pilot scope.')
    return rows


def publish_release(rows, manifest, config, *, client=None, embedder=None):
    """Create only. Existing names fail; a partial upload is never promoted or overwritten."""
    import os
    if config.backend == 'qdrant_cloud':
        from ai.qdrant_store import publish_qdrant_release
        return publish_qdrant_release(rows, manifest, config, client=client, embedder=embedder)
    require(config.backend == 'chroma_cloud', 'Cloud publication requires cloud configuration.')
    active = os.environ.get('SENTO_ACTIVE_COLLECTION')
    require(active and active != config.collection, 'Set SENTO_ACTIVE_COLLECTION to the serving collection, or NONE for first publication; never overwrite it.')
    from chromadb import Schema, VectorIndexConfig
    metadata = {**config.metadata(), 'coverage_json': json.dumps(manifest['expected_counts'], separators=(',', ':')),
                'reviewed_at': manifest['reviewed_at'], 'publication_status': 'building'}
    require(all(len(str(v).encode()) <= 256 for v in metadata.values()), 'Collection metadata exceeds cloud limits.')
    client = client or config.cloud_client()
    embedder = embedder or config.embedder()
    collection = client.create_collection(name=config.collection, embedding_function=None, metadata=metadata,
        schema=Schema().create_index(config=VectorIndexConfig(space='cosine')))
    for offset in range(0, len(rows), 32):
        batch = rows[offset:offset + 32]
        collection.add(ids=[r['index_id'] for r in batch], documents=[r['text'] for r in batch],
                       metadatas=[_metadata_for(r) for r in batch], embeddings=embedder.embed([r['text'] for r in batch]))
    verify_collection(collection, rows)
    collection.modify(metadata={**metadata, 'publication_status': 'ready'})
    return {'indexed': len(rows), 'collection': config.collection, 'status': 'ready_for_live_review'}


def verify_collection(collection, rows):
    expected = {r['index_id']: _metadata_for(r) for r in rows}
    observed = {}
    offset = 0
    while True:
        page = collection.get(limit=300, offset=offset, include=['metadatas'])
        ids = page.get('ids', [])
        observed.update(zip(ids, page.get('metadatas', [])))
        if len(ids) < 300:
            break
        offset += len(ids)
    require(observed == expected and collection.count() == len(rows), 'Uploaded IDs, provenance or counts do not match the release.')
