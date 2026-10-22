# Rewiring the Enterprise into a POSIX VFS: CI = Folder, Edge = Symlink

## Abstract & Thesis
Enterprise ITSM database architectures accumulate massive coordination bloat. By projecting configuration items (CIs) as directories and relationships as filesystem symlinks, transactional queries collapse to sub-microsecond POSIX readdir and stat calls on Linux NVMe pagecache.

## Canonical Lenses
- `POSIX_VFS_STATE_PLANE`
- `CI_FOLDER_EDGE_SYMLINK`
- `LATENCY_INVERSION_BOUNDARY`
- `ZERO_RAG_FILESYSTEM_GRAPH`
