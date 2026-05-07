import os
import uuid
import re
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_mestra_super_secreta_123")

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Decorator para proteger rotas
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return decorated_function


# --- ROTA DE LOGIN (INICIAL) ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_informado = request.form.get("email")
        password_informado = request.form.get("password")

        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM usuario WHERE email = %s", (email_informado,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        if not usuario:
            return render_template("login.html", erro="Usuário não encontrado!")

        if check_password_hash(usuario['senha'], password_informado):
            session["user"] = usuario['email']
            return redirect(url_for("listar_filmes"))
        else:
            return render_template("login.html", erro="Senha incorreta!")

    return render_template("login.html", erro=None)


# --- ROTA DE CADASTRO DE USUÁRIO ---
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        password = request.form.get("password")

        if len(password) < 8 or not re.search(r"[@#$%^&+=!]", password):
            return render_template("cadastro.html", erro="A senha deve ter 8+ caracteres e um símbolo (@#$%^&+=!)")

        senha_hash = generate_password_hash(password)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuario (nome, email, senha) VALUES (%s, %s, %s)", (nome, email, senha_hash))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for("login"))
        except Exception as ex:
            print(f"Erro no cadastro: {ex}")
            return render_template("cadastro.html", erro="Erro: E-mail já cadastrado ou falha no banco.")

    return render_template("cadastro.html", erro=None)


# --- LISTAR FILMES ---
@app.route('/filmes', methods=['GET'])
@login_required
def listar_filmes():
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM filmes ORDER BY id DESC")
        filmes = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("index.html", filmes=filmes)
    except Exception as ex:
        print(f"Erro ao listar filmes: {ex}")
        return render_template("erro.html", erro=str(ex))


# --- ADICIONAR NOVO FILME ---
@app.route("/novo", methods=["GET", "POST"])
@login_required
def novo_filme():
    if request.method == "POST":
        try:
            titulo = request.form.get("titulo")
            genero = request.form.get("genero")
            ano = request.form.get("ano")
            arquivo = request.files.get("imagem")

            if arquivo and allowed_file(arquivo.filename):
                extensao = arquivo.filename.rsplit('.', 1)[1].lower()
                nome_unico = f"{uuid.uuid4().hex}.{extensao}"
                caminho_fisico = os.path.join(app.config['UPLOAD_FOLDER'], nome_unico)
                arquivo.save(caminho_fisico)

                # Caminho relativo para o banco
                url_capa = f"uploads/{nome_unico}"
            else:
                return "Arquivo de imagem inválido ou não selecionado", 400

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO filmes (titulo, genero, ano, url_capa) VALUES (%s, %s, %s, %s)",
                (titulo, genero, ano, url_capa)
            )
            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for("listar_filmes"))
        except Exception as ex:
            print(f"--- ERRO NO CADASTRO DE FILME --- \n{ex}")
            return f"Erro ao cadastrar filme: {ex}", 500

    return render_template("novo_filme.html")


# --- EDITAR FILME ---
@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_filme(id):
    try:
        conn = get_connection()
        if request.method == "POST":
            titulo = request.form.get("titulo")
            genero = request.form.get("genero")
            ano = request.form.get("ano")
            url_capa = request.form.get("url_capa")  # Mantém a antiga se não mudar

            arquivo = request.files.get("imagem")
            if arquivo and allowed_file(arquivo.filename):
                extensao = arquivo.filename.rsplit('.', 1)[1].lower()
                nome_unico = f"{uuid.uuid4().hex}.{extensao}"
                arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_unico))
                url_capa = f"uploads/{nome_unico}"

            cursor = conn.cursor()
            cursor.execute(
                "UPDATE filmes SET titulo = %s, genero = %s, ano = %s, url_capa = %s WHERE id = %s",
                (titulo, genero, ano, url_capa, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for("listar_filmes"))

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM filmes WHERE id = %s", [id])
        filme = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template("editar_filme.html", filme=filme)
    except Exception as ex:
        print(f"Erro ao editar: {ex}")
        return f"Erro ao editar: {ex}", 500


# --- DELETAR FILME ---
@app.route("/deletar/<int:id>", methods=["POST"])
@login_required
def deletar_filme(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM filmes WHERE id = %s", [id])
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("listar_filmes"))
    except Exception as ex:
        print(f"Erro ao deletar: {ex}")
        return f"Erro ao deletar: {ex}", 500


# --- LOGOUT ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True)