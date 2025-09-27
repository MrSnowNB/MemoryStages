# MemoryStages Maintenance Guide

This document covers operational procedures for maintaining and administering MemoryStages installations.

## Vector Index Operations

### Index Rebuild Procedure

The vector index may need rebuilding after:
- Database corruption affects vector synchronization
- Vector store data loss (e.g., out-of-memory clearing)
- Upgrading vector store implementations
- Maintenance operations that invalidate the index

#### Safe Rebuild Process

1. **Ensure vector features are enabled:**
   ```bash
   export VECTOR_ENABLED=true
   export VECTOR_PROVIDER=memory  # or faiss
   export EMBED_PROVIDER=hash     # matching your config
   ```

2. **Create backup of current database (recommended):**
   ```bash
   cp ./data/memory.db ./data/memory-pre-rebuild.db
   ```

3. **Run the rebuild script:**
   ```bash
   python scripts/rebuild_index.py
   ```
   This will:
   - Clear the existing vector index
   - Re-embed all non-sensitive, non-tombstoned KV entries
   - Rebuild the vector index from canonical SQLite data

4. **Monitor progress and verify:**
   ```bash
   # Rebuild output should show:
   # ✓ Cleared existing vector index
   # Found X KV pairs in canonical store
   # Re-embedding Y non-sensitive KV pairs
   # ✓ Successfully rebuilt index with Y vectors
   # ✓ Verification search returned Z results
   ```

5. **Test search functionality:**
   ```bash
   # Enable search endpoint
   export SEARCH_API_ENABLED=true
   make dev

   # Test search
   curl "http://localhost:8000/search?query=test"
   ```

#### Failure Recovery

- If rebuild fails with embedding errors, check VECTOR_ENABLED and EMBED_PROVIDER settings
- If FAISS index fails, fall back to VECTOR_PROVIDER=memory
- If SQLite corruption is suspected, restore from backup and run rebuild

### Vector Store Providers

#### Memory Store (Default)
- **Pros**: Fast startup, no dependencies, persistent until process restart
- **Cons**: Data lost on restart, limited by available RAM
- **Maintenance**: Rebuilt on startup after data loss

#### FAISS Store (Production)
- **Pros**: Persistent index, better performance, scalable
- **Cons**: Additional dependency, more complex operations
- **Maintenance**: Index rebuild required after major updates

### Troubleshooting Vector Issues

#### Common Problems

**Search returning empty results:**
- Confirm VECTOR_ENABLED=true
- Run rebuild_index.py to repopulate
- Check for sensitive key filtering (expected behavior)

**Embedding failures:**
- Verify EMBED_PROVIDER configuration
- Check for missing dependencies (FAISS)
- Review error logs for specific failures

**Index corruption:**
- Run rebuild procedure immediately
- Check for out-of-memory conditions
- Consider switching to FAISS for production

## Database Maintenance

### Stage 6: Privacy-Protected Backup and Restore

Stage 6 introduces comprehensive backup and restore capabilities with privacy controls and automatic maintenance operations.

#### Encrypted Backup Procedure

**Configure Stage 6 features:**
```bash
# Enable required features
export BACKUP_ENABLED=true
export BACKUP_ENCRYPTION_ENABLED=true  # Recommended for security
export BACKUP_INCLUDE_SENSITIVE=false   # Exclude sensitive data by default
export MAINTENANCE_ENABLED=true         # Enable automatic maintenance

# Optional but recommended environment variables
export BACKUP_MASTER_PASSWORD="your-secure-backup-password-change-this"

# Required for privacy features
export PRIVACY_ENFORCEMENT_ENABLED=true
export PRIVACY_AUDIT_LEVEL=standard
```

**Create encrypted backup:**
```bash
# Create selective backup (recommended - excludes sensitive data)
python scripts/backup.py my_backup --encrypt

# Create full backup (includes sensitive data - requires admin confirmation)
python scripts/backup.py my_backup_full --include-sensitive --admin-confirmed

# Dry run to validate configuration without creating files
python scripts/backup.py my_backup --dry-run --verbose
```

**This creates two files:**
- `my_backup` - Encrypted backup data containing KV records, events, and vector data
- `my_backup.manifest.json` - Unencrypted manifest with metadata, checksums, and encryption keys

#### Privacy-Safe Restore Procedure

**Validate backup before restoration:**
```bash
# Dry run to check backup integrity without restoring
python scripts/restore.py my_backup my_backup.manifest.json --dry-run --verbose
```

**Restore from backup:**
```bash
# Restore from selective backup (no admin confirmation needed)
python scripts/restore.py my_backup my_backup.manifest.json

# Restore from full backup (requires admin confirmation if contains sensitive data)
python scripts/restore.py my_backup_full my_backup_full.manifest.json --admin-confirmed

# Interactive confirmation mode (default when not using --force)
python scripts/restore.py my_backup my_backup.manifest.json  # Will prompt for confirmation
```

#### Automated Maintenance Operations

**Run comprehensive maintenance suite:**
```bash
# Enable maintenance features
export MAINTENANCE_ENABLED=true

# Run all maintenance operations
python scripts/maintenance.py --full-maintenance

# Individual maintenance operations
python scripts/maintenance.py --check-integrity    # Database integrity check
python scripts/maintenance.py --validate-vectors   # Vector index validation
python scripts/maintenance.py --cleanup-orphans    # Remove orphaned data
python scripts/maintenance.py --rebuild-index      # Rebuild vector index
```

**Maintenance operation details:**
- **Database Integrity Check:** Validates SQLite schema, foreign keys, and data consistency
- **Vector Validation:** Cross-validates vector index with KV store, detects corruption
- **Orphaned Data Cleanup:** Removes vector entries without corresponding KV records
- **Vector Index Rebuild:** Recreates vector index from canonical SQLite data

**Get results in JSON format for automation:**
```bash
# Machine-readable output for monitoring systems
python scripts/maintenance.py --full-maintenance --json >> maintenance_log.json
```

### Legacy Backup Procedure (Stages 1-5)

```bash
# Stop the service first
pkill -f "uvicorn.*main:app"

# Backup database
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp ./data/memory.db ./data/memory_backup_${TIMESTAMP}.db

# Restart service
make dev
```

### Legacy Recovery from Backup (Stages 1-5)

```bash
# Restore database
cp ./data/memory_backup_TIMESTAMP.db ./data/memory.db

# Rebuild vector index if vector features enabled
VECTOR_ENABLED=true VECTOR_PROVIDER=memory EMBED_PROVIDER=hash \
python scripts/rebuild_index.py
```

#### Migration to Stage 6 Backup System

1. **Enable Stage 6 features** in environment variables
2. **Create initial Stage 6 backup** of current data
3. **Verify backup integrity** with dry-run restoration
4. **Test restoration** in a separate environment
5. **Update operational procedures** to use new backup/restore scripts

## Monitoring and Health Checks

### Automated Health Checks

```bash
# Service health
curl http://localhost:8000/health

# Expected response shows version and KV count
{
  "status": "healthy",
  "version": "1.0.0-stage1",
  "db_health": true,
  "kv_count": 42
}
```

### Key Metrics to Monitor

- Total KV pairs (from health endpoint)
- Search response times and hit rates
- Vector embedding success rates
- Database query performance

## Configuration Management

### Environment Variables Reference

See `docs/API_QUICKSTART.md` for complete variable list.

### Production Configuration

```bash
# Database
export DB_PATH=./data/production.db

# Vector features (enable for production)
export VECTOR_ENABLED=true
export VECTOR_PROVIDER=faiss  # Production store
export SEARCH_API_ENABLED=false  # Only enable if needed

# Security
export DEBUG=false  # Disable in production

# Optional FAISS configuration
pip install faiss-cpu
export VECTOR_PROVIDER=faiss
```

## Performance Considerations

### Memory Usage

- Memory store: ~4KB per embedded entry
- FAISS store: ~8KB per vector + overhead
- Embeddings: 384 floats (1.5KB) per entry with hash provider

### Optimization Tips

1. **Limit embedding operations:**
   - Don't embed sensitive data
   - Consider content size limits
   - Batch rebuild operations

2. **Index refresh frequency:**
   - For real-time: embed on every write
   - For bulk loads: rebuild periodically
   - For large datasets: consider FAISS rebuild intervals

3. **Search optimization:**
   - Default k=5 provides good balance
   - Increase k for broader results
   - Monitor response times

## Upgrade Procedures

### Future Stage Transitions

When upgrading to future stages:

1. **Backup current database**
2. **Note current configuration**
3. **Deploy new code**
4. **Run upgrade scripts if needed**
5. **Rebuild vector index if schema changes**
6. **Verify all endpoints**

### Rollback Procedures

1. **Restore database backup**
2. **Revert to previous code version**
3. **Rebuild vector index**
4. **Verify functionality**

## Emergency Procedures

### Data Loss Response

1. **Assess damage:** Check database integrity and vector index state
2. **Isolate service:** Stop accepting writes if corruption suspected
3. **Restore from backup:** Use most recent clean backup
4. **Rebuild components:** Run SQL integrity checks and vector rebuild
5. **Verify and restart:** Test all endpoints before resuming operation

### Memory Management Crisis

1. **Memory store:** Clear index and rebuild
   ```bash
   python scripts/rebuild_index.py
   ```
2. **FAISS store:** Monitor index size or rebuild
3. **Temporary mitigation:** Disable VECTOR_ENABLED if needed

## Contact and Support

For issues not covered here:
1. Check application logs
2. Review recent configuration changes
3. Test in isolated environment
4. Document findings for support requests
