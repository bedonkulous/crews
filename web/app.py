"""Flask application factory for the crews web UI."""

from __future__ import annotations

from flask import Flask, render_template

from web.api.crews import crews_bp
from web.api.env import env_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = "dev-local-only"

    app.register_blueprint(crews_bp, url_prefix="/api")
    app.register_blueprint(env_bp, url_prefix="/api")

    @app.route("/")
    @app.route("/crews")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/crews/new")
    def crew_create():
        return render_template("crew_create.html")

    @app.route("/crews/<name>")
    def crew_detail(name: str):
        return render_template("crew_detail.html", crew_name=name)

    @app.route("/env")
    def env_page():
        return render_template("env.html")

    return app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
