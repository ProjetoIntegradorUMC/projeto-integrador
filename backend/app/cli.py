import click

from app import db
from app.models import User


def register_cli(app):
    @app.cli.command("provision-admin")
    @click.argument("email")
    @click.option("--revoke", is_flag=True, help="Remove o acesso administrativo.")
    def provision_admin(email, revoke):
        """Concede (ou remove, com --revoke) o acesso ao painel de auditoria."""
        user = User.query.filter_by(email=email).first()
        if not user:
            raise click.ClickException(f"Nenhum usuário com o e-mail {email}.")

        click.echo(
            f"Usuário: id={user.id} username={user.username} nome={user.full_name}"
        )
        acao = "Remover" if revoke else "Conceder"
        if not click.confirm(f"{acao} acesso administrativo a esta conta?"):
            raise click.Abort()

        user.is_admin = not revoke
        db.session.commit()
        click.echo("Acesso removido." if revoke else "Acesso concedido.")
