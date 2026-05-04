"""
╔══════════════════════════════════════════════════════════════════╗
║  SYNAPSE PROTOCOL — Python SDK (LangChain-Compatible)          ║
║                                                                ║
║  Classe principal para integração com LangChain, LlamaIndex    ║
║  e qualquer framework Python de agentes de IA.                 ║
║                                                                ║
║  PRIVACY-FIRST: Toda encriptação/decriptação acontece         ║
║  AQUI no client. O servidor Supabase NUNCA vê texto plano.     ║
║                                                                ║
║  Uso:                                                          ║
║    from synapse_memory import SynapseMemory                    ║
║    memory = SynapseMemory(                                     ║
║        supabase_url="https://...",                             ║
║        supabase_key="eyJ...",                                  ║
║        user_password="senha-do-usuario",                       ║
║    )                                                           ║
║    memory.store("Usuário mora em São Paulo")                   ║
║    results = memory.recall("onde o usuário mora?")             ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# For cache TTL tracking
import time as monotonic_time

# ─── Criptografia (AES-256-GCM client-side) ─────────────────────────────────
# Usa a lib nativa 'cryptography' para compatibilidade máxima.
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ─── Supabase Client ────────────────────────────────────────────────────────
from supabase import create_client, Client as SupabaseClient

# ─── LangChain Compatibility ────────────────────────────────────────────────
# Importação condicional para não forçar dependência do LangChain
try:
    from langchain_core.memory import BaseMemory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Se LangChain não estiver instalado, usa classe base genérica
    BaseMemory = object  # type: ignore
    LANGCHAIN_AVAILABLE = False


# ─── Constantes Criptográficas ───────────────────────────────────────────────

# Tamanho da chave AES-256 em bytes
_KEY_LENGTH = 32

# Tamanho do IV para AES-GCM (12 bytes — padrão NIST SP 800-38D)
_IV_LENGTH = 12

# Tamanho do salt para PBKDF2
_SALT_LENGTH = 32

# Iterações PBKDF2 (OWASP 2024+ recomenda ≥ 210.000 para SHA-256)
_PBKDF2_ITERATIONS = 210_000

# Categorias de intenção suportadas
INTENT_CATEGORIES = [
    "preference",    # Preferências do usuário
    "fact",          # Fatos sobre o usuário/contexto
    "instruction",   # Instruções e regras
    "emotion",       # Estado emocional
    "goal",          # Objetivos e metas
    "relationship",  # Relações entre entidades
    "skill",         # Habilidades e capacidades
    "context",       # Contexto geral da sessão
]


# ─── Tipos de Dados ─────────────────────────────────────────────────────────


@dataclass
class EncryptedPayload:
    """
    Payload criptografado pronto para envio ao servidor.

    O servidor armazena este blob — NUNCA vê o conteúdo original.
    Decriptação acontece exclusivamente no client SDK.
    """

    ciphertext: str  # Ciphertext + auth tag em Base64
    iv: str          # Initialization Vector em Base64
    salt: str        # Salt PBKDF2 em Base64
    version: int = 1 # Versão do schema de encriptação

    def to_json(self) -> str:
        """Serializa para JSON (para armazenar como string no DB)."""
        return json.dumps({
            "ct": self.ciphertext,
            "iv": self.iv,
            "s": self.salt,
            "v": self.version,
        })

    @classmethod
    def from_json(cls, raw: str) -> "EncryptedPayload":
        """Deserializa de JSON."""
        data = json.loads(raw)
        return cls(
            ciphertext=data["ct"],
            iv=data["iv"],
            salt=data["s"],
            version=data.get("v", 1),
        )


@dataclass
class Memory:
    """
    Representa uma memória do Synapse Layer.

    O campo 'content' só é preenchido após decriptação no client.
    O campo 'content_encrypted' contém o blob opaco do servidor.
    """

    id: str
    user_id: str
    content: Optional[str] = None            # Texto plano (só no client!)
    content_encrypted: Optional[str] = None  # Blob AES-256-GCM
    intent_category: str = "context"
    importance_score: float = 0.5
    fact_hash: str = ""
    context_signature: str = ""
    similarity: Optional[float] = None       # Score de similaridade (busca)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


# ─── Funções Criptográficas ─────────────────────────────────────────────────


def _derive_key(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Deriva chave AES-256 a partir da senha do usuário via PBKDF2.

    PBKDF2 com 210.000 iterações de SHA-256 torna ataques de
    força bruta computacionalmente inviáveis (~200ms por tentativa).

    Args:
        password: Senha ou passphrase do usuário
        salt: Salt existente (para re-derivar). Se None, gera novo.

    Returns:
        Tupla (key: 32 bytes, salt: 32 bytes)
    """
    if salt is None:
        salt = os.urandom(_SALT_LENGTH)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    return key, salt


def _encrypt(plaintext: str, password: str) -> EncryptedPayload:
    """
    Encripta texto com AES-256-GCM (client-side).

    O servidor NUNCA vê o plaintext — apenas o blob resultante.

    Args:
        plaintext: Texto a encriptar
        password: Senha do usuário

    Returns:
        EncryptedPayload pronto para envio ao servidor
    """
    # 1. Derivar chave via PBKDF2
    key, salt = _derive_key(password)

    # 2. Gerar IV aleatório (12 bytes — padrão NIST)
    iv = os.urandom(_IV_LENGTH)

    # 3. Encriptar com AES-256-GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

    return EncryptedPayload(
        ciphertext=b64encode(ciphertext).decode("ascii"),
        iv=b64encode(iv).decode("ascii"),
        salt=b64encode(salt).decode("ascii"),
        version=1,
    )


def _decrypt(payload: EncryptedPayload, password: str) -> str:
    """
    Decripta payload AES-256-GCM (client-side).

    Args:
        payload: Payload criptografado do servidor
        password: Mesma senha usada na encriptação

    Returns:
        Texto original descriptografado

    Raises:
        ValueError: Se a senha estiver errada ou dados corrompidos
    """
    ciphertext = b64decode(payload.ciphertext)
    iv = b64decode(payload.iv)
    salt = b64decode(payload.salt)

    # Re-derivar chave com o mesmo salt
    key, _ = _derive_key(password, salt)

    try:
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(
            "Falha na decriptação: senha incorreta ou dados corrompidos. "
            f"Detalhes: {e}"
        )


def _generate_fact_hash(content: str) -> str:
    """
    Gera hash SHA-256 determinístico para detecção de conflitos.

    O fact hash permite detectar memórias contraditórias SEM
    descriptografar o conteúdo no servidor.

    Args:
        content: Conteúdo original (antes da encriptação)

    Returns:
        SHA-256 hex string do conteúdo normalizado
    """
    normalized = " ".join(content.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _generate_context_signature(
    user_id: str, intent_category: str, session_id: str
) -> str:
    """
    Gera assinatura de contexto para tracking de sessão.

    Usada pelo Neural Handover™ para manter linhagem entre modelos.

    Args:
        user_id: ID do usuário
        intent_category: Categoria da intenção
        session_id: ID da sessão

    Returns:
        Context signature (16 caracteres hex)
    """
    payload = f"{user_id}:{intent_category}:{session_id}:{time.time()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ─── Classe Principal ───────────────────────────────────────────────────────


class SynapseMemory(BaseMemory):
    """
    Synapse Layer Memory — LangChain-Compatible.

    Camada de memória persistente com encriptação AES-256-GCM. Server never sees plaintext.
    Funciona como drop-in replacement para qualquer BaseMemory do LangChain.

    A encriptação/decriptação acontece INTEIRAMENTE nesta classe.
    O servidor Supabase armazena apenas blobs AES-256-GCM opacos.

    Attributes:
        supabase_url: URL do projeto Supabase
        supabase_key: Chave anon do Supabase (client-side safe)
        user_id: UUID do usuário
        user_password: Senha para derivação da chave AES-256
        embedding_fn: Função que gera embeddings (1536 dims)
        session_id: ID da sessão atual

    Example:
        >>> from synapse_memory import SynapseMemory
        >>> memory = SynapseMemory(
        ...     supabase_url="https://xxx.supabase.co",
        ...     supabase_key="eyJ...",
        ...     user_id="550e8400-e29b-41d4-a716-446655440000",
        ...     user_password="minha-senha-forte",
        ...     embedding_fn=my_embedding_function,
        ... )
        >>> memory.store("Usuário prefere respostas em português")
        >>> results = memory.recall("idioma preferido")
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        user_id: str,
        user_password: str,
        embedding_fn: Any = None,
        session_id: Optional[str] = None,
        cache_ttl_seconds: float = 2.0,
    ):
        """
        Inicializa o SDK de memória do Synapse Layer.

        Args:
            supabase_url: URL do projeto Supabase
            supabase_key: Chave anon (public) do Supabase
            user_id: UUID do usuário autenticado
            user_password: Senha para derivação de chave AES-256 (NUNCA sai do client)
            embedding_fn: Callable que recebe texto e retorna list[float] (1536 dims).
                         Se None, embeddings devem ser passados manualmente.
            session_id: ID da sessão (auto-gerado se omitido)
            cache_ttl_seconds: TTL do cache em segundos (padrão: 2.0s, 0 para desabilitar)
        """
        # Inicializar BaseMemory do LangChain se disponível
        if LANGCHAIN_AVAILABLE and BaseMemory is not object:
            super().__init__()

        self._supabase: SupabaseClient = create_client(supabase_url, supabase_key)
        self._user_id = user_id
        self._password = user_password
        self._embedding_fn = embedding_fn
        self._session_id = session_id or str(uuid.uuid4())

        # Cache da chave derivada (evita re-derivar a cada operação)
        self._derived_key: Optional[bytes] = None
        self._derived_salt: Optional[bytes] = None
        
        # Cache TTL for recall() results
        self._cache_ttl: float = float(cache_ttl_seconds)
        self._cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    # ─── Cache Methods ────────────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[Any]:
        """
        Return cached value if not expired, else None.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key in self._cache:
            value, expires_at = self._cache[key]
            if monotonic_time.monotonic() < expires_at:
                return value
            del self._cache[key]
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        """
        Store value in cache with TTL expiry.

        Args:
            key: Cache key
            value: Value to cache
        """
        if self._cache_ttl > 0:
            expires_at = monotonic_time.monotonic() + self._cache_ttl
            self._cache[key] = (value, expires_at)

    def _cache_invalidate(self, key: str) -> None:
        """
        Remove a specific key from cache.

        Args:
            key: Cache key to remove
        """
        self._cache.pop(key, None)

    def _cache_clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    # ─── LangChain Interface ─────────────────────────────────────────────

    @property
    def memory_variables(self) -> List[str]:
        """Variáveis de memória expostas ao LangChain."""
        return ["synapse_context"]

    def load_memory_variables(
        self, inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Carrega memórias relevantes para o LangChain.

        Busca as top-10 memórias mais relevantes baseado no input
        e retorna como contexto formatado.

        Args:
            inputs: Dict com chave 'input' contendo a query do usuário

        Returns:
            Dict com chave 'synapse_context' contendo memórias formatadas
        """
        query = (inputs or {}).get("input", "")
        if not query:
            return {"synapse_context": ""}

        # Buscar memórias relevantes
        memories = self.recall(query, top_k=10, threshold=0.7)

        if not memories:
            return {"synapse_context": ""}

        # Formatar memórias para injeção no prompt
        formatted = "\n".join(
            f"[{m.intent_category}|{m.importance_score:.1f}] {m.content}"
            for m in memories
            if m.content  # Só inclui se descriptografou com sucesso
        )

        return {"synapse_context": formatted}

    def save_context(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> None:
        """
        Salva contexto da interação como memória.

        Chamado automaticamente pelo LangChain após cada interação.

        Args:
            inputs: Input do usuário
            outputs: Output do modelo
        """
        # Salvar input do usuário como memória
        user_input = inputs.get("input", "")
        if user_input:
            self.store(
                content=user_input,
                intent_category="context",
                importance_score=0.5,
            )

        # Salvar output do modelo como memória (menor importância)
        model_output = outputs.get("output", "")
        if model_output:
            self.store(
                content=model_output,
                intent_category="context",
                importance_score=0.3,
            )

    def clear(self) -> None:
        """Limpa memórias da sessão (marca como inativas)."""
        self._supabase.from_("memories").update(
            {"is_active": False}
        ).eq("user_id", self._user_id).execute()

    # ─── Core API ────────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        intent_category: str = "context",
        importance_score: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Armazena uma nova memória com encriptação AES-256-GCM — server never sees plaintext.

        Fluxo:
        1. Gera embedding do texto plano (local ou via API)
        2. Encripta conteúdo com AES-256-GCM (client-side)
        3. Calcula fact_hash para detecção de conflitos
        4. Envia ao Supabase: embedding + blob criptografado
        5. Servidor NUNCA vê o texto original

        Args:
            content: Texto da memória (será criptografado localmente)
            intent_category: Categoria semântica (preference, fact, etc.)
            importance_score: Importância de 0.0 a 1.0
            metadata: Metadados adicionais (opcional)
            embedding: Vetor de embedding pré-calculado (opcional)

        Returns:
            UUID da memória criada

        Raises:
            ValueError: Se intent_category é inválida
            RuntimeError: Se embedding_fn não configurada e embedding não fornecido
        """
        # Validar categoria
        if intent_category not in INTENT_CATEGORIES:
            raise ValueError(
                f"intent_category deve ser um de: {INTENT_CATEGORIES}. "
                f"Recebido: '{intent_category}'"
            )

        # 1. Gerar embedding (se não fornecido)
        if embedding is None:
            if self._embedding_fn is None:
                raise RuntimeError(
                    "embedding_fn não configurada. Passe embedding_fn no construtor "
                    "ou forneça embedding manualmente."
                )
            embedding = self._embedding_fn(content)

        # 2. Encriptar conteúdo (AES-256-GCM — acontece aqui no client!)
        encrypted = _encrypt(content, self._password)

        # 3. Gerar fact hash (para detecção de conflitos sem decriptar)
        fact_hash = _generate_fact_hash(content)

        # 4. Gerar context signature
        ctx_sig = _generate_context_signature(
            self._user_id, intent_category, self._session_id
        )

        # 5. Criar registro
        memory_id = str(uuid.uuid4())
        record = {
            "id": memory_id,
            "user_id": self._user_id,
            "content_encrypted": encrypted.to_json(),  # Blob opaco!
            "embedding": embedding,
            "intent_category": intent_category,
            "importance_score": importance_score,
            "fact_hash": fact_hash,
            "is_active": True,
            "context_signature": ctx_sig,
            "metadata": metadata or {},
        }

        # 6. Inserir no Supabase (servidor vê apenas blob + embedding)
        result = self._supabase.from_("memories").insert(record).execute()

        if hasattr(result, "error") and result.error:
            raise RuntimeError(f"Erro ao armazenar memória: {result.error}")

        # Invalidate cache after successful write
        self._cache_clear()

        return memory_id

    def recall(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7,
        intent_filter: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> List[Memory]:
        """
        Busca semântica de memórias (com decriptação client-side).

        Fluxo:
        1. Gera embedding da query
        2. Busca via pgvector (HNSW) no Supabase
        3. Servidor retorna blobs criptografados
        4. Client decripta cada memória localmente
        5. Retorna memórias com texto plano

        Args:
            query: Texto da busca (será convertido em embedding)
            top_k: Máximo de resultados
            threshold: Threshold mínimo de similaridade coseno
            intent_filter: Filtrar por categoria (opcional)
            embedding: Embedding pré-calculado (opcional)

        Returns:
            Lista de Memory com conteúdo descriptografado
        """
        # 0. Check cache before Supabase call
        cache_key = f"recall:{self._user_id}:{query[:64]}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # 1. Gerar embedding da query
        if embedding is None:
            if self._embedding_fn is None:
                raise RuntimeError(
                    "embedding_fn não configurada. Passe embedding_fn no construtor "
                    "ou forneça embedding manualmente."
                )
            embedding = self._embedding_fn(query)

        # 2. Busca semântica via RPC match_memories (pgvector HNSW)
        result = self._supabase.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_count": top_k,
                "match_threshold": threshold,
                "p_user_id": self._user_id,
            },
        ).execute()

        if not result.data:
            result_memories = []
        else:
            # 3. Decriptar cada memória (AES-256-GCM: decriptação client-side!)
            memories: List[Memory] = []
            for row in result.data:
                # Filtrar por intent se especificado
                if intent_filter and row.get("intent_category") != intent_filter:
                    continue

                # Tentar decriptar conteúdo
                content = None
                try:
                    encrypted_json = row.get("content_encrypted", "")
                    if encrypted_json:
                        payload = EncryptedPayload.from_json(encrypted_json)
                        content = _decrypt(payload, self._password)
                except (ValueError, json.JSONDecodeError) as e:
                    # Log erro mas não falha — pode ser memória de outra sessão
                    content = f"[ERRO DECRIPTAÇÃO: {e}]"

                memories.append(
                    Memory(
                        id=row["id"],
                        user_id=self._user_id,
                        content=content,
                        content_encrypted=row.get("content_encrypted"),
                        intent_category=row.get("intent_category", "context"),
                        importance_score=row.get("importance_score", 0.5),
                        fact_hash=row.get("fact_hash", ""),
                        context_signature=row.get("context_signature", ""),
                        similarity=row.get("similarity"),
                        metadata=row.get("metadata", {}),
                        created_at=row.get("created_at"),
                    )
                )

            result_memories = memories

        # Cache the result before returning
        self._cache_set(cache_key, result_memories)
        return result_memories

    def create_handover(
        self,
        source_model: str,
        session_summary: str,
        intent_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Cria um pacote Neural Handover™ para transferência entre modelos.

        O contexto da sessão é criptografado antes do envio.
        O session_summary é o ÚNICO texto plano (sem dados sensíveis).

        Args:
            source_model: Nome do modelo atual (e.g., "claude-3.5-sonnet")
            session_summary: Resumo de alto nível da sessão
            intent_state: Estado das intenções ativas

        Returns:
            Dict com handover_id e metadados
        """
        # Buscar memórias ativas da sessão
        result = self._supabase.from_("memories").select(
            "id, content_encrypted, intent_category, importance_score, context_signature"
        ).eq(
            "user_id", self._user_id
        ).eq(
            "is_active", True
        ).order(
            "importance_score", desc=True
        ).limit(20).execute()

        active_memories = result.data or []

        # Encriptar contexto da sessão
        session_context_encrypted = _encrypt(
            json.dumps({
                "session_id": self._session_id,
                "source_model": source_model,
                "intent_state": intent_state or {},
                "memory_count": len(active_memories),
            }),
            self._password,
        ).to_json()

        # Criar registro de handover
        handover_id = str(uuid.uuid4())
        handover = {
            "id": handover_id,
            "user_id": self._user_id,
            "source_model": source_model,
            "session_context": session_context_encrypted,
            "session_summary": session_summary,
            "active_memories": active_memories,
            "intent_state": intent_state or {},
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "expires_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(time.time() + 86400),  # 24h TTL
            ),
        }

        self._supabase.from_("handovers").insert(handover).execute()

        return {
            "success": True,
            "handover_id": handover_id,
            "memories_included": len(active_memories),
            "expires_at": handover["expires_at"],
        }

    def load_handover(
        self, handover_id: str, target_model: str
    ) -> Dict[str, Any]:
        """
        Carrega um pacote Neural Handover™ de outro modelo.

        Args:
            handover_id: UUID do pacote de handover
            target_model: Nome do modelo atual (e.g., "gpt-4o")

        Returns:
            Dict com contexto completo da sessão anterior

        Raises:
            ValueError: Se handover não encontrado ou expirado
        """
        result = self._supabase.from_("handovers").select(
            "*"
        ).eq(
            "id", handover_id
        ).eq(
            "status", "pending"
        ).single().execute()

        if not result.data:
            raise ValueError(f"Handover {handover_id} não encontrado ou já consumido.")

        handover = result.data

        # Marcar como consumido
        self._supabase.from_("handovers").update({
            "target_model": target_model,
            "status": "consumed",
        }).eq("id", handover_id).execute()

        # Decriptar contexto da sessão
        session_context = None
        try:
            payload = EncryptedPayload.from_json(handover["session_context"])
            session_context = json.loads(_decrypt(payload, self._password))
        except Exception:
            session_context = {"error": "Falha ao decriptar contexto da sessão"}

        return {
            "success": True,
            "handover_id": handover_id,
            "source_model": handover["source_model"],
            "target_model": target_model,
            "session_summary": handover.get("session_summary", ""),
            "session_context": session_context,
            "active_memories": handover.get("active_memories", []),
            "intent_state": handover.get("intent_state", {}),
        }

    # ─── Utilitários ─────────────────────────────────────────────────────

    def get_active_count(self) -> int:
        """Retorna o número de memórias ativas do usuário."""
        result = self._supabase.from_("memories").select(
            "id", count="exact"
        ).eq("user_id", self._user_id).eq("is_active", True).execute()
        return result.count or 0

    def get_context_summary(self) -> Dict[str, int]:
        """
        Retorna resumo do contexto por categoria.

        Útil para o Intent-to-Context Pipeline (redução de 60-80% de tokens).

        Returns:
            Dict mapeando intent_category → contagem de memórias
        """
        result = self._supabase.from_("memories").select(
            "intent_category"
        ).eq("user_id", self._user_id).eq("is_active", True).execute()

        summary: Dict[str, int] = {}
        for row in (result.data or []):
            cat = row.get("intent_category", "unknown")
            summary[cat] = summary.get(cat, 0) + 1

        return summary

    def __repr__(self) -> str:
        return (
            f"SynapseMemory(user_id='{self._user_id}', "
            f"session='{self._session_id}', "
            f"encrypted=True)"
        )
