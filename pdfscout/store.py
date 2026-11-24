"""In-memory document sessions with undo/redo history."""

from __future__ import annotations

import itertools
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator

import pymupdf

from . import core


_version_ids = itertools.count(1)


@dataclass
class Session:
    id: str
    filename: str
    versions: list[bytes]
    labels: list[str]
    ids: list[int] = field(default_factory=lambda: [next(_version_ids)])
    index: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)
    touched: float = field(default_factory=time.time)
    _doc: pymupdf.Document | None = None
    _doc_index: int = -1

    @property
    def version(self) -> int:
        """Unique id of the current state (never reused, safe for caching)."""
        return self.ids[self.index]

    def doc(self) -> pymupdf.Document:
        """Read-only handle to the current version (cached)."""
        if self._doc is None or self._doc_index != self.index:
            if self._doc is not None:
                self._doc.close()
            self._doc = pymupdf.open("pdf", self.versions[self.index])
            self._doc_index = self.index
        return self._doc

    def can_undo(self) -> bool:
        return self.index > 0

    def can_redo(self) -> bool:
        return self.index < len(self.versions) - 1

    def state(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "version": self.version,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "undo_label": self.labels[self.index] if self.can_undo() else None,
            "redo_label": self.labels[self.index + 1] if self.can_redo() else None,
            "size": len(self.versions[self.index]),
        }


class DocumentStore:
    def __init__(self, max_history: int = 40, ttl_seconds: int = 6 * 3600, max_sessions: int = 50):
        self.max_history = max_history
        self.ttl = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, data: bytes, filename: str = "document.pdf", password: str | None = None) -> Session:
        doc = core.open_bytes(data, password)
        rewrite = bool(doc.is_encrypted or password)
        if not doc.is_pdf:
            rewrite = True
            pdf = doc.convert_to_pdf()
            doc.close()
            doc = pymupdf.open("pdf", pdf)
            if not filename.lower().endswith(".pdf"):
                filename = filename.rsplit(".", 1)[0] + ".pdf"
        if doc.page_count == 0:
            raise core.PDFScoutError("Document has no pages")
        # store an unencrypted copy so later operations don't need the password
        if rewrite:
            data = doc.tobytes(garbage=1, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
        doc.close()
        sess = Session(id=uuid.uuid4().hex, filename=filename, versions=[data], labels=["Open"])
        with self._lock:
            self._evict()
            self._sessions[sess.id] = sess
        return sess

    def get(self, sid: str) -> Session:
        with self._lock:
            sess = self._sessions.get(sid)
        if sess is None:
            raise KeyError(sid)
        sess.touched = time.time()
        return sess

    def delete(self, sid: str) -> None:
        with self._lock:
            sess = self._sessions.pop(sid, None)
        if sess and sess._doc is not None:
            sess._doc.close()

    def _evict(self) -> None:
        now = time.time()
        for sid, s in list(self._sessions.items()):
            if now - s.touched > self.ttl:
                self._sessions.pop(sid, None)
        while len(self._sessions) >= self.max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s.touched)
            self._sessions.pop(oldest.id, None)

    @contextmanager
    def edit(self, sid: str, label: str) -> Iterator[pymupdf.Document]:
        """Open a writable copy; on success commit it as a new version."""
        sess = self.get(sid)
        with sess.lock:
            doc = pymupdf.open("pdf", sess.versions[sess.index])
            try:
                yield doc
                data = doc.tobytes(garbage=3, deflate=True)
            finally:
                doc.close()
            del sess.versions[sess.index + 1 :]
            del sess.labels[sess.index + 1 :]
            del sess.ids[sess.index + 1 :]
            sess.versions.append(data)
            sess.labels.append(label)
            sess.ids.append(next(_version_ids))
            sess.index += 1
            overflow = len(sess.versions) - self.max_history
            if overflow > 0:
                del sess.versions[:overflow]
                del sess.labels[:overflow]
                del sess.ids[:overflow]
                sess.index -= overflow
                sess._doc_index = -1

    def apply(self, sid: str, label: str, fn: Callable[[pymupdf.Document], object]) -> object:
        with self.edit(sid, label) as doc:
            return fn(doc)

    def undo(self, sid: str) -> Session:
        sess = self.get(sid)
        with sess.lock:
            if sess.can_undo():
                sess.index -= 1
        return sess

    def redo(self, sid: str) -> Session:
        sess = self.get(sid)
        with sess.lock:
            if sess.can_redo():
                sess.index += 1
        return sess
