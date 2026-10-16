from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest

from app.utils.sessions import revoke_all_user_sessions


def test_revoke_all_user_sessions_marca_revoked_at_em_todas_as_sessoes():
    """Garante que revoke_all_user_sessions preenche revoked_at em todas as sessões ativas (Issue #83)."""
    mock_session_1 = MagicMock()
    mock_session_1.revoked_at = None
    mock_session_2 = MagicMock()
    mock_session_2.revoked_at = None

    active_sessions = [mock_session_1, mock_session_2]

    with patch("app.utils.sessions.Session") as mock_session_cls, \
         patch("app.utils.sessions.db.session") as mock_db_session:

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.all.return_value = active_sessions
        mock_query.filter.return_value = mock_filter
        mock_session_cls.query = mock_query

        count = revoke_all_user_sessions(user_id=42, commit=True)

        assert count == 2
        assert mock_session_1.revoked_at is not None
        assert mock_session_2.revoked_at is not None
        mock_db_session.commit.assert_called_once()


def test_revoke_all_user_sessions_atomicidade_sem_commit():
    """Valida se commit=False permite atomicidade com a transação principal de troca de senha."""
    mock_session = MagicMock()
    mock_session.revoked_at = None

    with patch("app.utils.sessions.Session") as mock_session_cls, \
         patch("app.utils.sessions.db.session") as mock_db_session:

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.all.return_value = [mock_session]
        mock_query.filter.return_value = mock_filter
        mock_session_cls.query = mock_query

        count = revoke_all_user_sessions(user_id=10, commit=False)

        assert count == 1
        assert mock_session.revoked_at is not None
        mock_db_session.commit.assert_not_called()


def test_revoke_all_user_sessions_quando_usuario_nao_tem_sessoes():
    """Verifica comportamento quando o usuário não possui nenhuma sessão ativa."""
    with patch("app.utils.sessions.Session") as mock_session_cls, \
         patch("app.utils.sessions.db.session") as mock_db_session:

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.all.return_value = []
        mock_query.filter.return_value = mock_filter
        mock_session_cls.query = mock_query

        count = revoke_all_user_sessions(user_id=99, commit=True)

        assert count == 0
        mock_db_session.commit.assert_called_once()
