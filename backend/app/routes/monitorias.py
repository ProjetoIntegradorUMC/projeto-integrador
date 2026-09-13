from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Inscricao, Monitoria
from app.utils.sessions import login_required


monitorias_bp = Blueprint("monitorias", __name__)


def serialize_monitoria(monitoria):
    return {
        "id": monitoria.id,
        "disciplina": monitoria.disciplina,
        "descricao": monitoria.descricao,
        "status": monitoria.status,
        "monitor": {
            "id": monitoria.monitor.id,
            "username": monitoria.monitor.username,
        },
    }


@monitorias_bp.route("", methods=["GET"])
@login_required
def list_monitorias(current_user):
    monitorias = Monitoria.query.filter(
        Monitoria.status == "disponivel",
        Monitoria.monitor_id != current_user.id,
    ).order_by(Monitoria.id.desc()).all()

    return jsonify({"monitorias": [serialize_monitoria(item) for item in monitorias]})


@monitorias_bp.route("", methods=["POST"])
@login_required
def create_monitoria(current_user):
    data = request.get_json() or {}
    disciplina = str(data.get("disciplina") or "").strip()
    descricao = str(data.get("descricao") or "").strip()

    if not disciplina or not descricao:
        return jsonify({"error": "Disciplina e descrição são obrigatórias"}), 400

    monitoria = Monitoria(
        monitor_id=current_user.id,
        disciplina=disciplina,
        descricao=descricao,
    )
    db.session.add(monitoria)
    db.session.commit()

    return jsonify({"message": "Monitoria oferecida com sucesso"}), 201


@monitorias_bp.route("/<int:monitoria_id>/inscricoes", methods=["POST"])
@login_required
def create_inscricao(current_user, monitoria_id):
    monitoria = db.session.get(Monitoria, monitoria_id)

    if not monitoria or monitoria.status != "disponivel":
        return jsonify({"error": "Monitoria não encontrada ou indisponível"}), 404

    if monitoria.monitor_id == current_user.id:
        return jsonify({"error": "Você não pode se inscrever na própria monitoria"}), 400

    inscricao = Inscricao(usuario_id=current_user.id, monitoria_id=monitoria.id)
    db.session.add(inscricao)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Você já está inscrito nesta monitoria"}), 409

    return jsonify({"message": "Inscrição realizada com sucesso"}), 201


@monitorias_bp.route("/minhas", methods=["GET"])
@login_required
def list_user_monitorias(current_user):
    oferecidas = Monitoria.query.filter_by(monitor_id=current_user.id).order_by(
        Monitoria.id.desc()
    )
    inscricoes = Inscricao.query.filter_by(usuario_id=current_user.id).order_by(
        Inscricao.id.desc()
    )

    return jsonify(
        {
            "oferecidas": [serialize_monitoria(item) for item in oferecidas],
            "inscricoes": [
                {
                    "id": inscricao.id,
                    "status": inscricao.status,
                    "monitoria": serialize_monitoria(inscricao.monitoria),
                }
                for inscricao in inscricoes
            ],
        }
    )
