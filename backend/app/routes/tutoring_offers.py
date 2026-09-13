from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Enrollment, TutoringOffer
from app.utils.sessions import login_required


tutoring_offers_bp = Blueprint("tutoring_offers", __name__)


def serialize_tutoring_offer(tutoring_offer):
    return {
        "id": tutoring_offer.id,
        "disciplina": tutoring_offer.subject,
        "descricao": tutoring_offer.description,
        "status": tutoring_offer.status,
        "monitor": {
            "id": tutoring_offer.mentor.id,
            "full_name": tutoring_offer.mentor.full_name,
        },
    }


@tutoring_offers_bp.route("", methods=["GET"])
@login_required
def list_tutoring_offers(current_user):
    tutoring_offers = TutoringOffer.query.filter(
        TutoringOffer.status == "available",
        TutoringOffer.mentor_id != current_user.id,
        ~TutoringOffer.enrollments.any(Enrollment.user_id == current_user.id),
    ).order_by(TutoringOffer.id.desc()).all()

    return jsonify({"monitorias": [serialize_tutoring_offer(item) for item in tutoring_offers]})


@tutoring_offers_bp.route("", methods=["POST"])
@login_required
def create_tutoring_offer(current_user):
    data = request.get_json() or {}
    subject = str(data.get("disciplina") or "").strip()
    description = str(data.get("descricao") or "").strip()

    if not subject or not description:
        return jsonify({"error": "Disciplina e descrição são obrigatórias"}), 400

    tutoring_offer = TutoringOffer(
        mentor_id=current_user.id,
        subject=subject,
        description=description,
    )
    db.session.add(tutoring_offer)
    db.session.commit()

    return jsonify({"message": "Monitoria oferecida com sucesso"}), 201


@tutoring_offers_bp.route("/<int:tutoring_offer_id>/enrollments", methods=["POST"])
@login_required
def create_enrollment(current_user, tutoring_offer_id):
    tutoring_offer = db.session.get(TutoringOffer, tutoring_offer_id)

    if not tutoring_offer or tutoring_offer.status != "available":
        return jsonify({"error": "Monitoria não encontrada ou indisponível"}), 404

    if tutoring_offer.mentor_id == current_user.id:
        return jsonify({"error": "Você não pode se inscrever na própria monitoria"}), 400

    enrollment = Enrollment(
        user_id=current_user.id,
        tutoring_offer_id=tutoring_offer.id,
    )
    db.session.add(enrollment)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Você já está inscrito nesta monitoria"}), 409

    return jsonify({"message": "Inscrição realizada com sucesso"}), 201


@tutoring_offers_bp.route(
    "/<int:tutoring_offer_id>/enrollment", methods=["DELETE"]
)
@login_required
def delete_enrollment(current_user, tutoring_offer_id):
    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        tutoring_offer_id=tutoring_offer_id,
    ).first()

    if not enrollment:
        return jsonify({"error": "Inscrição não encontrada"}), 404

    db.session.delete(enrollment)
    db.session.commit()

    return jsonify({"message": "Inscrição cancelada com sucesso"}), 200


@tutoring_offers_bp.route("/mine", methods=["GET"])
@login_required
def list_user_tutoring_offers(current_user):
    offered_offers = TutoringOffer.query.filter_by(mentor_id=current_user.id).order_by(
        TutoringOffer.id.desc()
    )
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).order_by(
        Enrollment.id.desc()
    )

    return jsonify(
        {
            "oferecidas": [serialize_tutoring_offer(item) for item in offered_offers],
            "inscricoes": [
                {
                    "id": enrollment.id,
                    "status": enrollment.status,
                    "monitoria": serialize_tutoring_offer(enrollment.tutoring_offer),
                }
                for enrollment in enrollments
            ],
        }
    )
