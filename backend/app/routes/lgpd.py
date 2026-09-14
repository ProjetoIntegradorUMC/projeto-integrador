from flask import Blueprint, jsonify, make_response
from app import db
from app.models import User
from app.utils.sessions import login_required

lgpd_bp = Blueprint("lgpd", __name__)

@lgpd_bp.route("/export", methods=["GET"])
@login_required
def export_data(current_user):
    """
    LGPD (Art. 18): Direito de acesso e portabilidade.
    Exporta os dados pessoais do usuário em formato JSON, omitindo dados sensíveis de segurança.
    """
    user_data = {
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "two_factor_enabled": current_user.two_factor_enabled,
    }
    
    # Verifica a existência dinâmica dos campos de consentimento, garantindo
    # compatibilidade retroativa caso a funcionalidade de LGPD-Terms não esteja carregada.
    if hasattr(current_user, 'consent_given_at'):
        user_data["consent_given_at"] = current_user.consent_given_at.isoformat() if current_user.consent_given_at else None
        if hasattr(current_user, 'consent_version'):
            user_data["consent_version"] = current_user.consent_version

    offers = []
    for offer in current_user.tutoring_offers:
        offers.append({
            "id": offer.id,
            "subject": offer.subject,
            "description": offer.description,
            "status": offer.status
        })
    user_data["tutoring_offers"] = offers

    enrollments = []
    for enrollment in current_user.enrollments:
        enrollments.append({
            "id": enrollment.id,
            "tutoring_offer_id": enrollment.tutoring_offer_id,
            "status": enrollment.status
        })
    user_data["enrollments"] = enrollments

    return jsonify({"user": user_data}), 200

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
