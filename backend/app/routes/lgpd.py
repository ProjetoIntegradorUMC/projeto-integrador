from flask import Blueprint, jsonify, make_response
from app import db
from app.models import User
from app.utils.sessions import login_required

lgpd_bp = Blueprint("lgpd", __name__)


def _status_label(status, default="Não informado"):
    return {
        "available": "Disponível",
        "active": "Ativa",
    }.get(status, default)


@lgpd_bp.route("/export", methods=["GET"])
@login_required
def export_data(current_user):
    """
    LGPD (Art. 18): Direito de acesso e portabilidade.
    Exporta os dados pessoais do usuário em formato JSON, omitindo dados sensíveis de segurança.
    """
    personal_data = {
        "Nome completo": current_user.full_name,
        "Nome de usuário": current_user.username,
        "E-mail": current_user.email,
        "Autenticação em dois fatores": (
            "Ativada" if current_user.two_factor_enabled else "Desativada"
        ),
    }

    if hasattr(current_user, 'consent_given_at'):
        consent_data = {
            "Registrado em": (
                current_user.consent_given_at.isoformat()
                if current_user.consent_given_at
                else None
            )
        }
        if hasattr(current_user, 'consent_version'):
            consent_data["Versão"] = current_user.consent_version
        personal_data["Consentimento"] = consent_data

    offers = []
    for offer in current_user.tutoring_offers:
        offers.append({
            "Disciplina": offer.subject,
            "Descrição": offer.description,
            "Situação": _status_label(offer.status),
        })

    enrollments = []
    for enrollment in current_user.enrollments:
        enrollments.append({
            "Disciplina": enrollment.tutoring_offer.subject,
            "Descrição": enrollment.tutoring_offer.description,
            "Situação da inscrição": _status_label(
                enrollment.status, default="Não informada"
            ),
        })

    return jsonify(
        {
            "Dados pessoais": personal_data,
            "Monitorias oferecidas": offers,
            "Inscrições em monitorias": enrollments,
        }
    ), 200

@lgpd_bp.route("/delete", methods=["DELETE"])
@login_required
def delete_account(current_user):
    """
    LGPD (Art. 18): Direito à eliminação dos dados.
    Deleta a conta do usuário. O ON DELETE CASCADE configurado nos models
    garante que sessões, inscrições e monitorias sejam apagadas em cascata.
    """
    db.session.delete(current_user)
    db.session.commit()
    
    response = make_response(jsonify({"message": "Conta e dados pessoais excluídos com sucesso."}))
    response.set_cookie("session_id", "", expires=0)
    return response, 200
