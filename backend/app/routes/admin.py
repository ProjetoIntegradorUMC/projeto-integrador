import os
from flask import Blueprint, jsonify
from app.utils.sessions import login_required
from app.models import SecurityLog, PasswordResetLog

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/logs", methods=["GET"])
@login_required
def get_logs(current_user):
    """
    Retorna os logs de segurança e métricas agregadas para o Painel de Auditoria.
    O acesso é restrito estritamente a administradores. Para evitar a criação
    desnecessária de novos campos no banco de dados (princípio de minimização),
    utilizamos uma variável de ambiente ADMIN_EMAIL para validar a autorização.
    """
    admin_email = os.environ.get("ADMIN_EMAIL")
    
    # Se a variável não estiver configurada ou o e-mail não bater, bloqueia o acesso
    if not admin_email or current_user.email != admin_email:
        return jsonify({"error": "Acesso negado. Requer privilégios de administrador."}), 403

    # Agregação de métricas de segurança (Security Logs)
    login_success = SecurityLog.query.filter_by(event_type="login_success").count()
    login_failure = SecurityLog.query.filter_by(event_type="login_failure").count()
    twofa_failure = SecurityLog.query.filter_by(event_type="twofa_failure").count()

    # Agregação de métricas de recuperação de senha (Password Reset Logs)
    password_reset_requests = PasswordResetLog.query.filter_by(event_type="request").count()

    # Busca os eventos mais recentes para montar a listagem
    # Limitamos a 20 registros de cada para não sobrecarregar a memória
    recent_security_logs = SecurityLog.query.order_by(SecurityLog.created_at.desc()).limit(20).all()
    recent_password_logs = PasswordResetLog.query.order_by(PasswordResetLog.created_at.desc()).limit(20).all()

    # Padroniza os dicionários para facilitar o consumo pelo Front-end
    events = []
    for log in recent_security_logs:
        events.append({
            "id": f"sec_{log.id}",
            "type": log.event_type,
            "email": log.email,
            "reason": log.failure_reason or "N/A",
            "created_at": log.created_at.isoformat(),
            "source": "SecurityLog"
        })

    for log in recent_password_logs:
        events.append({
            "id": f"pwd_{log.id}",
            "type": f"password_{log.event_type}", # ex: password_request
            "email": log.email,
            "reason": log.failure_reason or "N/A",
            "created_at": log.created_at.isoformat(),
            "source": "PasswordResetLog"
        })

    # Mescla as duas listas e ordena pela data mais recente (ordem decrescente)
    events.sort(key=lambda x: x["created_at"], reverse=True)

    # Retorna apenas os 20 mais recentes de todo o sistema
    top_events = events[:20]

    return jsonify({
        "metrics": {
            "login_success": login_success,
            "login_failure": login_failure,
            "twofa_failure": twofa_failure,
            "password_reset_requests": password_reset_requests
        },
        "recent_events": top_events
    }), 200
